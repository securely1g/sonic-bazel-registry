"""Preserve public library/SDK tar contracts using declared ELF inspection."""
from pathlib import PurePosixPath
import sys
import tarfile
from elf_metadata import Elf

seen_runtime = set(); seen_debug = set(); seen_dev_archives = set(); sdk = 0
for path in sys.argv[1:]:
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
