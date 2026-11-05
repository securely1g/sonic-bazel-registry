"""Check the installed libteam SDK and all five matching debug-symbol pairs.

Adapted from sonic-buildimage 233bde22 src/libteam/verify_runtime.py. The
registry test is self-contained; it retains the installed header/pkg-config,
ELF identity, isolated missing-symbol and positive GDB checks of that test.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shlex
import shutil
import struct
import subprocess
import tarfile
import tempfile
import zlib


def require(condition, message):
    if not condition:
        raise ValueError(message)


def command(*args, **kwargs):
    return subprocess.check_output(args, text=True, stderr=subprocess.STDOUT, **kwargs)


def verify_development_timestamps(development):
    """Reject build-time metadata in the exported development archive."""
    with tarfile.open(development) as archive:
        members = archive.getmembers()
        require(members, "empty development archive")
        for member in members:
            require(member.mtime == 0,
                    "non-reproducible development timestamp: " + member.name)
    return len(members)


def files(archive):
    with tarfile.open(archive) as payload:
        members = payload.getmembers()
        require(len({m.name for m in members}) == len(members), "duplicate archive path")
        for member in members:
            require(not member.name.startswith('/') and '..' not in Path(member.name).parts,
                    "unsafe archive path")
            require((member.uid, member.gid) == (0, 0), "non-root archive ownership")
        return {member.name: member for member in members}


def extract(archive, root):
    files(archive)
    with tarfile.open(archive) as payload:
        payload.extractall(root, filter='data')


def build_id(path):
    match = re.search(r'Build ID: ([0-9a-f]+)', command('readelf', '-n', str(path)))
    require(match is not None, "ELF lacks a build ID: " + str(path))
    return match[1]


# Preserve the accepted sonic-buildimage 233bde22 structured lookup: a stripped
# executable may lack even a minimal symbol, making `info line main` a GDB
# command error. Missing debug symbols are a result, not a failed GDB process.
GDB_SCRIPT = r'''python
import gdb, json, re
result = {"found": False}
try:
    requested_symbol = __SONIC_DEBUG_SYMBOL__
    candidates = [requested_symbol] if requested_symbol else []
    for line in ([] if requested_symbol else gdb.execute("info functions", to_string=True).splitlines()):
        match = re.match(r"^\s*\d+:\s+(.+);\s*$", line)
        if not match:
            continue
        name = match.group(1).split("(", 1)[0].split()[-1]
        if re.fullmatch(r"[A-Za-z_~][\w:<>~]*", name):
            candidates.append(name)
    for name in candidates[:200]:
        try:
            locations = gdb.decode_line(name)[1] or []
            for location in locations:
                if not location.symtab or location.line <= 0:
                    continue
                block = gdb.block_for_pc(location.pc)
                while block is not None and block.function is None:
                    block = block.superblock
                symbol = block.function if block is not None else None
                if symbol is None or symbol.type.code != gdb.TYPE_CODE_FUNC:
                    continue
                result = {"found": True, "function": symbol.name,
                          "source": location.symtab.filename, "line": location.line,
                          "type": str(symbol.type),
                          "parameters": [str(field.type) for field in symbol.type.fields()]}
                break
            if result["found"]:
                break
        except Exception:
            continue
except Exception as error:
    result["error"] = str(error)
print("SONIC_DEBUG_LOOKUP=" + json.dumps(result))
end
'''


def gdb_lookup(binary, symbol_dir, symbol):
    with tempfile.TemporaryDirectory(prefix='libteam-gdb-') as directory:
        script = Path(directory) / 'lookup.gdb'
        script.write_text(GDB_SCRIPT.replace('__SONIC_DEBUG_SYMBOL__', repr(symbol)))
        result = subprocess.run(
            ['gdb', '-nx', '-nh', '--batch',
             '-iex', 'set auto-load off', '-iex', 'set debuginfod enabled off',
             '-iex', 'set pagination off',
             '-iex', 'set debug-file-directory ' + str(symbol_dir),
             '-ex', 'file ' + json.dumps(str(binary)), '-x', str(script)],
            text=True, capture_output=True, timeout=300,
            env=dict(os.environ, LC_ALL='C', DEBUGINFOD_URLS='', LD_BIND_NOW='1'))
    records = [line.removeprefix('SONIC_DEBUG_LOOKUP=') for line in result.stdout.splitlines()
               if line.startswith('SONIC_DEBUG_LOOKUP=')]
    require(result.returncode == 0 and len(records) == 1,
            'GDB did not return one successful lookup result: ' + json.dumps({
                'returncode': result.returncode, 'stdout': result.stdout[-16000:],
                'stderr': result.stderr[-4000:]}))
    lookup = json.loads(records[0])
    require(isinstance(lookup, dict) and type(lookup.get('found')) is bool and 'error' not in lookup,
            'GDB returned an invalid lookup result: ' + records[0])
    return lookup


def verify(args):
    machine, triplet = {'x86_64': (62, 'x86_64-linux-gnu'),
                        'aarch64': (183, 'aarch64-linux-gnu')}[platform.machine()]
    libdir = 'usr/lib/' + triplet
    expected = {
        'libteam': [(libdir + '/libteam.so.5.6.1', 'team_alloc', 'libteam.c')],
        'libteamdctl': [(libdir + '/libteamdctl.so.0.1.5', 'teamdctl_alloc', 'libteamdctl.c')],
        'libteam_utils': [('usr/bin/teamd', 'main', 'teamd.c'),
                          ('usr/bin/teamnl', 'main', 'teamnl.c'),
                          ('usr/bin/teamdctl', 'main', 'teamdctl.c')],
    }
    sdk_members = verify_development_timestamps(args.development)
    full = json.loads(args.metadata.read_text())
    libraries = json.loads(args.library_metadata.read_text())
    require(full['module'] == libraries['module'] == 'libteam', 'metadata has the wrong source owner')
    require(full['architecture'] == libraries['architecture'] == ('amd64' if machine == 62 else 'arm64'),
            'metadata architecture does not match the ELF target')
    require(set(full['packages']) == {'libteam5', 'libteamdctl0', 'libteam-utils'},
            'full metadata must describe all three delivered packages')
    require(libraries['packages'] == {name: full['packages'][name] for name in ['libteam5', 'libteamdctl0']},
            'library metadata must preserve both library records and omit utilities')
    for package, archive in [('libteam5', args.libteam), ('libteamdctl0', args.libteamdctl),
                             ('libteam-utils', args.libteam_utils)]:
        record = full['packages'][package]
        require(record['payload_sha256'] == hashlib.sha256(archive.read_bytes()).hexdigest(),
                'metadata does not identify the delivered payload: ' + package)
        require(record['control_fields']['Package'] == package and record['control_fields']['Version'] == '1.31-1',
                'metadata changed the Debian package identity')
    pairs = []
    with tempfile.TemporaryDirectory(prefix='libteam-installed-') as directory:
        root = Path(directory)
        extract(args.dependency_development, root)
        for name, entries in expected.items():
            runtime = getattr(args, name)
            symbols = getattr(args, name + '_symbols')
            members = files(runtime)
            with tarfile.open(runtime) as archive:
                actual_elfs = {m.name for m in archive.getmembers() if m.isfile()
                               and archive.extractfile(m).read(4) == b'\x7fELF'}
            require(actual_elfs == {row[0] for row in entries}, 'unexpected installed ELF set: ' + name)
            extract(runtime, root)
            extract(symbols, root)
            for path, symbol, source in entries:
                require(members[path].mode == (0o755 if path.startswith('usr/bin/') else 0o644),
                        'incorrect installed ELF mode: ' + path)
                binary = root/path
                header = binary.read_bytes()[:64]
                require(header[:6] == b'\x7fELF\x02\x01' and struct.unpack_from('<H', header, 18)[0] == machine,
                        'incorrect native ELF architecture')
                identifier = build_id(binary)
                debug = root/'usr/lib/debug/.build-id'/identifier[:2]/(identifier[2:] + '.debug')
                require(debug.is_file() and build_id(debug) == identifier, 'missing matching detached symbols')
                require(debug.stat().st_mode & 0o777 == 0o644, 'incorrect detached symbol mode')
                require('.debug_info' not in command('readelf', '-SW', str(binary)), 'runtime contains DWARF')
                sections = command('readelf', '-SW', str(debug))
                require('.debug_info' in sections and '.debug_line' in sections, 'detached DWARF is incomplete')
                link = root/(name + '-' + binary.name + '.debuglink')
                command('objcopy', '--dump-section=.gnu_debuglink=' + str(link), str(binary), str(root/'elf-copy'))
                data = link.read_bytes(); end = data.index(b'\0')
                require(data[:end].decode() == debug.name and
                        struct.unpack_from('<I', data, (end+4)&~3)[0] == zlib.crc32(debug.read_bytes()),
                        'detached debuglink CRC mismatch')
                empty = root/'empty-symbols'; empty.mkdir(exist_ok=True)
                isolated = root/'isolated'/name; isolated.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(binary, isolated/binary.name)
                negative = gdb_lookup(isolated/binary.name, empty, symbol)
                require(not negative['found'], 'debug lookup escaped its isolated directory')
                positive = gdb_lookup(binary, root/'usr/lib/debug', symbol)
                require(positive['found'] and positive.get('source', '').endswith(source) and positive.get('line', 0) > 0,
                        'packaged symbols do not resolve owner source: ' + path)
                if name != 'libteam_utils':
                    version = '5.6.1' if name == 'libteam' else '0.1.5'
                    soname = name + '.so.' + version.split('.')[0]
                    require('[' + soname + ']' in command('readelf', '-d', str(binary)), 'incorrect library SONAME')
                    symlink = members[libdir + '/' + soname]
                    require(symlink.issym() and symlink.linkname == name + '.so.' + version, 'incorrect runtime SONAME link')
                pairs.append({'path':path, 'build_id':identifier, 'missing_symbols_rejected':True,
                              'source':source, 'sha256':hashlib.sha256(binary.read_bytes()).hexdigest()})

        sdk = files(args.development)
        for name in ['team.h', 'teamdctl.h']:
            item = sdk['usr/include/' + name]
            require(item.isfile() and item.mode == 0o644, 'incorrect installed public header')
        for name, version in [('libteam', '5.6.1'), ('libteamdctl', '0.1.5')]:
            item = sdk[libdir + '/' + name + '.so']
            require(item.issym() and item.linkname == name + '.so.' + version, 'incorrect SDK link')
        extract(args.development, root)
        env = dict(os.environ, PKG_CONFIG_PATH='', PKG_CONFIG_LIBDIR=str(root/libdir/'pkgconfig'),
                   PKG_CONFIG_SYSROOT_DIR=str(root))
        for name in ['libteam', 'libteamdctl']:
            require(command('pkg-config', '--modversion', name, env=env).strip() == '1.31', 'incorrect installed pkg-config version')
            require(command('pkg-config', '--variable=includedir', name, env=env).strip() == str(root/'usr/include'), 'incorrect installed include path')
        flags = shlex.split(command('pkg-config', '--cflags', 'libteam', 'libteamdctl', env=env))
        libs = shlex.split(command('pkg-config', '--libs', 'libteam', 'libteamdctl', env=env))
        require({'-lteam', '-lteamdctl', '-lnl-3', '-L' + str(root/libdir)} <= set(libs), 'incorrect installed linker interface')
        command('cc', '-std=c11', '-Wall', '-Wextra', '-Werror', *flags, '-c', str(args.consumer), '-o', str(root/'consumer.o'))
        require(struct.unpack_from('<H', (root/'consumer.o').read_bytes(), 18)[0] == machine, 'SDK compiler is not native')

    return {'scope':'Installed native SDK and five symbol pairs; daemon networking and OCI are separate acceptance',
            'development_timestamps':{'mtime':0, 'members':sdk_members}, 'pairs':pairs}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['libteam','libteamdctl','libteam-utils']:
        parser.add_argument('--'+name, type=Path, required=True)
        parser.add_argument('--'+name+'-symbols', type=Path, required=True)
    for name in ['development','dependency-development','consumer','metadata','library-metadata']:
        parser.add_argument('--'+name, type=Path, required=True)
    args=parser.parse_args()
    result=verify(args)
    print(json.dumps(result, indent=2))
    output=os.environ.get('TEST_UNDECLARED_OUTPUTS_DIR')
    if output:
        (Path(output)/'installed-libteam.json').write_text(json.dumps(result, indent=2)+'\n')


if __name__ == '__main__':
    main()
