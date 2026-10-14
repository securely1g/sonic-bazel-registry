"""Validate the installed iproute2 package against Debian's program manifest."""
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import tarfile
import tempfile
import zlib


def command(*args, **kwargs):
    return subprocess.check_output(args, text=True, stderr=subprocess.STDOUT, **kwargs)


def build_id(path):
    match = re.search(r"Build ID: ([0-9a-f]+)", command("readelf", "-n", str(path)))
    assert match, path
    return match.group(1)


def main():
    runtime, debug, config, manifest, *libraries = [Path(value).resolve() for value in sys.argv[1:]]
    expected = {}
    for line in manifest.read_text().splitlines():
        parts = line.split()
        if not parts or not parts[0].startswith('sbin/') or parts[0] == 'sbin/routel':
            continue
        name = Path(parts[0]).name
        destination = parts[1].strip('/') if len(parts) > 1 else 'sbin'
        if destination in ('bin', 'sbin'):
            destination = 'usr/' + destination
        expected[name] = destination + '/' + name
    assert len(expected) == 15, expected
    configuration = config.read_text()
    for feature in ('HAVE_LIBBPF', 'HAVE_ELF', 'HAVE_MNL', 'HAVE_BERKELEY_DB', 'HAVE_RPC', 'HAVE_SELINUX', 'HAVE_CAP', 'TC_CONFIG_XT'):
        assert re.search(r'^' + feature + r'\s*:=\s*y$', configuration, re.M), feature
    # Trixie glibc provides strlcpy itself; the original configure script
    # selects libbsd only when libc lacks it. Neither path uses the fallback.
    assert '-DNEED_STRLCPY' not in configuration
    assert 'CONF_COLOR:=COLOR_OPT_AUTO' in configuration
    source = manifest.parent.parent
    with tempfile.TemporaryDirectory(dir=os.environ['TEST_TMPDIR']) as temporary:
        root = Path(temporary)
        for archive in [*libraries, runtime]:
            with tarfile.open(archive) as package:
                package.extractall(root, filter='data')
        with tarfile.open(runtime) as package:
            actual = set()
            for member in package.getmembers():
                assert (member.uid, member.gid) == (0, 0), member.name
                if member.isfile() and package.extractfile(member).read(4) == b'\x7fELF':
                    actual.add(member.name)
                    assert member.mode == 0o755, member.name
            assert actual == set(expected.values()), actual
        for relative, original in (
            ('usr/share/iproute2/rt_protos', 'etc/iproute2/rt_protos'),
            ('usr/bin/routel', 'ip/routel'),
            ('usr/include/iproute2/bpf_elf.h', 'include/bpf_elf.h'),
            ('usr/share/doc/iproute2/copyright', 'debian/copyright'),
        ):
            assert (root / relative).read_bytes() == (source / original).read_bytes(), relative
        assert os.readlink(root / 'usr/bin/ctstat') == 'lnstat'
        assert os.readlink(root / 'usr/bin/rtstat') == 'lnstat'
        assert (root / 'usr/sbin/ip').resolve() == root / 'usr/bin/ip'
        assert not list(root.glob('usr/**/ifstat*')), 'Debian excludes the conflicting ifstat program'
        tables = list(root.glob('usr/lib/*-linux-gnu/tc/*.dist'))
        assert {path.stem for path in tables} == {'normal', 'pareto', 'paretonormal', 'experimental'}
        assert all(path.stat().st_size > 1000 for path in tables)
        assert (root / 'usr/share/man/man8/ip.8').is_file()
        assert (root / 'usr/share/bash-completion/completions/tc').is_file()

        loaders = {path.resolve() for path in root.rglob('ld-linux-*.so.*') if path.is_file()}
        assert len(loaders) == 1, loaders
        search = sorted({str(path.parent) for path in root.rglob('*.so*') if path.is_file()})
        prefix = [str(loaders.pop()), '--inhibit-cache', '--library-path', os.pathsep.join(search)]
        environment = dict(os.environ)
        for name in ('LD_PRELOAD', 'LD_LIBRARY_PATH', 'LD_AUDIT'):
            environment.pop(name, None)

        def debugger(binary):
            return subprocess.run(['gdb', '-nx', '-batch', '-ex', 'set debuginfod enabled off',
                                   '-ex', f'set debug-file-directory {root}/usr/lib/debug',
                                   '-ex', f'file {binary}', '-ex', 'info line main'],
                                  text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout

        identities = {}
        for name, relative in expected.items():
            binary = root / relative
            listing = command(*prefix, '--list', str(binary), env=environment)
            assert 'not found' not in listing, listing
            resolved = re.findall(r'=> (/\S+)', listing)
            assert resolved and all(Path(path).resolve().is_relative_to(root) for path in resolved), listing
            assert not re.search(r'\((?:RPATH|RUNPATH)\)', command('readelf', '-d', str(binary)))
            assert '.debug_info' not in command('readelf', '-SW', str(binary))
            assert not re.search(r'Line \d+ of', debugger(binary))
            identities[name] = build_id(binary)
        for name in ('ip', 'tc', 'ss'):
            output = command(*prefix, str(root / expected[name]), '-V', env=environment)
            assert '6.15.0' in output, output
        # Debian's patch must be applied before the SONiC bridge patch.
        moo = subprocess.run([*prefix, str(root / expected['ip']), 'moo'],
                             env=environment, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        assert moo.returncode == 1 and 'no real cows were harmed' in moo.stdout, moo.stdout
        # Read-only netlink query: no namespace, link or route changes.
        interfaces = json.loads(command(*prefix, str(root / expected['ip']), '-j', 'link', 'show', 'dev', 'lo', env=environment))
        assert len(interfaces) == 1 and interfaces[0]['ifname'] == 'lo', interfaces
        help_result = subprocess.run([*prefix, str(root / expected['bridge']), 'fdb', 'help'],
                                     env=environment, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        assert '[ proto PROTO ]' in help_result.stdout, help_result.stdout
        with tarfile.open(debug) as package:
            package.extractall(root, filter='data')
        for name, identity in identities.items():
            binary = root / expected[name]
            symbols = root / 'usr/lib/debug/.build-id' / identity[:2] / (identity[2:] + '.debug')
            assert build_id(symbols) == identity
            assert '.debug_info' in command('readelf', '-SW', str(symbols))
            section = root / (name + '.debuglink')
            command('objcopy', '--dump-section', f'.gnu_debuglink={section}', str(binary), str(root / (name + '.copy')))
            link = section.read_bytes()
            assert link.split(b'\0', 1)[0].decode() == symbols.name
            assert struct.unpack('<I', link[-4:])[0] == zlib.crc32(symbols.read_bytes())
            location = debugger(binary)
            assert re.search(r'Line \d+ of .*' + re.escape(name + '.c'), location), location
        print('All15 installed programs match Debian manifest; source features, protocol option, private libraries, netlink read and debug symbols passed')


if __name__ == '__main__':
    main()
