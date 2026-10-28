"""Preserve public library/SDK tar contracts using declared ELF inspection."""
import argparse
from pathlib import PurePosixPath
import tarfile
import zlib
from elf_metadata import Elf

STEMS = ('libnl-3', 'libnl-route-3', 'libnl-genl-3', 'libnl-nf-3', 'libnl-cli-3')
PLUGINS = (
    'cls/basic', 'cls/cgroup', 'qdisc/bfifo', 'qdisc/blackhole', 'qdisc/fq_codel',
    'qdisc/hfsc', 'qdisc/htb', 'qdisc/ingress', 'qdisc/pfifo', 'qdisc/plug',
)


def contents(path):
    with tarfile.open(path) as archive:
        files = {}
        for entry in archive:
            if entry.isdir():
                continue
            name = entry.name.removeprefix('./')
            assert name not in files, ('duplicate archive member', path, name)
            files[name] = (entry, archive.extractfile(entry).read() if entry.isfile() else None)
    assert files, path
    return files


def check_debug_pair(name, payload, debug_files):
    elf = Elf(payload)
    assert elf.build_id, (name, 'missing build ID')
    debug_path = 'usr/lib/debug/.build-id/' + elf.build_id[:2] + '/' + elf.build_id[2:] + '.debug'
    assert debug_path in debug_files, (name, 'missing paired debug file', debug_path)
    entry, symbols = debug_files[debug_path]
    assert entry.isfile() and entry.uid == entry.gid == 0
    symbol_elf = Elf(symbols)
    assert symbol_elf.build_id == elf.build_id, (name, 'different debug build ID')
    for section in ('.debug_info', '.debug_line'):
        assert section not in elf.by_name, (name, 'unstripped runtime', section)
        assert section in symbol_elf.by_name, (name, 'missing debug information', section)
    assert elf.debuglink == PurePosixPath(debug_path).name, (name, 'different debug-link filename')
    assert elf.debuglink_crc == zlib.crc32(symbols), (name, 'different debug-link CRC')
    return debug_path


def check_split_archives(core, route, runtime_paths, debug_paths):
    """Retain the published Debian file splits independently of aggregate SDKs."""
    core_files, route_files = contents(core), contents(route)
    archives = [name for name in core_files if name.endswith('/libnl-3.a')]
    assert len(archives) == 1, archives
    prefix = archives[0].removesuffix('libnl-3.a')
    assert prefix in ('usr/lib/x86_64-linux-gnu/', 'usr/lib/aarch64-linux-gnu/'), prefix
    dev_names = set()
    for files, stem in ((core_files, 'libnl-3'), (route_files, 'libnl-route-3')):
        headers = {name for name in files if name.startswith('usr/include/libnl3/netlink/') and name.endswith('.h')}
        if stem == 'libnl-3':
            assert len(headers) > 100, len(headers)
            assert {'usr/include/libnl3/netlink/version.h', 'usr/include/libnl3/netlink/route/route.h'} <= headers
        else:
            assert not headers, headers
        expected = {prefix + stem + suffix for suffix in ('.a', '.so')}
        expected.add(prefix + 'pkgconfig/' + stem + '.0.pc')
        expected |= headers
        assert set(files) == expected, (stem, set(files) ^ expected)
        assert not set(files) & dev_names, (stem, set(files) & dev_names)
        dev_names.update(files)
        for name, (entry, payload) in files.items():
            assert entry.uid == entry.gid == 0, name
            if name.endswith('.so'):
                assert entry.issym() and entry.linkname == stem + '.so.200', name
            else:
                assert entry.isfile() and entry.mode == 0o644, (name, entry.mode)
            if name.endswith('.a'):
                assert payload.startswith(b'!<arch>\n'), name

    runtime_names = set()
    assert len(runtime_paths) == len(debug_paths) == len(STEMS)
    for stem, runtime_path, debug_path in zip(STEMS, runtime_paths, debug_paths):
        files, debug_files = contents(runtime_path), contents(debug_path)
        expected = {prefix + stem + suffix for suffix in ('.so.200', '.so.200.26.0')}
        if stem == 'libnl-3':
            expected |= {'etc/libnl-3/classid', 'etc/libnl-3/pktloc'}
        if stem == 'libnl-cli-3':
            expected |= {prefix + 'libnl-3/cli/' + plugin + '.so' for plugin in PLUGINS}
        assert set(files) == expected, (stem, set(files) ^ expected)
        assert not set(files) & (dev_names | runtime_names), stem
        runtime_names.update(files)
        paired_debug = set()
        for name, (entry, payload) in files.items():
            assert entry.uid == entry.gid == 0, name
            if name == prefix + stem + '.so.200':
                assert entry.issym() and entry.linkname == stem + '.so.200.26.0', name
            else:
                assert entry.isfile() and entry.mode == 0o644, (name, entry.mode)
                if name.startswith(prefix):
                    assert payload.startswith(b'\x7fELF'), name
                    elf = Elf(payload)
                    assert elf.machine == (62 if 'x86_64' in prefix else 183), name
                    if name == prefix + stem + '.so.200.26.0':
                        assert elf.soname == stem + '.so.200', (name, elf.soname)
                    paired_debug.add(check_debug_pair(name, payload, debug_files))
        assert set(debug_files) == paired_debug, (stem, set(debug_files) ^ paired_debug)



def check_aggregate_archives(paths):
    seen_runtime = set(); seen_debug = set(); seen_dev_archives = set(); sdk = 0
    for path in paths:
        with tarfile.open(path) as archive:
            files = {entry.name.removeprefix('./'): (entry, archive.extractfile(entry).read() if entry.isfile() else None) for entry in archive if not entry.isdir()}
        assert files
        for name, (entry, payload) in files.items():
            assert entry.uid == entry.gid == 0
            assert 'linux-private/' not in name and 'netlink-private/' not in name
            if entry.issym():
                assert not entry.linkname.startswith('/')
            if payload and payload.startswith(b'\x7fELF'):
                elf = Elf(payload)
                if name.startswith('usr/lib/debug/'):
                    assert elf.build_id
                    assert name.endswith(elf.build_id[:2] + '/' + elf.build_id[2:] + '.debug')
                    seen_debug.add(elf.build_id)
                elif elf.soname and elf.soname.startswith('libnl-'):
                    assert name.endswith(elf.soname + '.26.0')
                    assert 'usr/lib/' in name
                    seen_runtime.add(elf.soname)
            if name.endswith('.a'):
                assert payload.startswith(b'!<arch>\n')
                seen_dev_archives.add(PurePosixPath(name).name)
        if 'usr/include/libnl3/netlink/netlink.h' in files:
            assert 'usr/include/libnl3/netlink/route/route.h' in files
            sdk += 1
        for name, (entry, payload) in files.items():
            if name.endswith('.pc'):
                text = payload.decode()
                assert 'Version: 3.7.0\n' in text
                assert 'includedir=${prefix}/include\n' in text
                assert 'libdir=${prefix}/lib/' in text
                assert '-I${includedir}' in text
    assert seen_runtime == {stem + '.so.200' for stem in ['libnl-3','libnl-genl-3','libnl-route-3','libnl-nf-3','libnl-cli-3']}
    assert seen_debug
    assert {'libnl-3.a','libnl-route-3.a'} <= seen_dev_archives
    assert sdk == 6  # Five legacy aggregate SDKs plus the exact core dev_files.


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('aggregate', nargs='+')
    parser.add_argument('--dev-core', required=True)
    parser.add_argument('--dev-route', required=True)
    parser.add_argument('--runtime', action='append', required=True)
    parser.add_argument('--debug', action='append', required=True)
    args = parser.parse_args()
    check_aggregate_archives(args.aggregate)
    check_split_archives(args.dev_core, args.dev_route, args.runtime, args.debug)
    print('Aggregate SDKs, exact disjoint file splits and all 15 runtime/debug ELF pairs verified')


if __name__ == '__main__':
    main()
