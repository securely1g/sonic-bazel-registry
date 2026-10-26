"""Check Debian install contracts using archive data and declared ELF metadata."""
import gzip
from pathlib import Path
import struct
import sys
import tarfile
import zlib

from elf_metadata import Elf


def contents(path):
    with tarfile.open(path) as archive:
        members = {entry.name.removeprefix('./'): entry for entry in archive}
        data = {name: archive.extractfile(entry).read() for name, entry in members.items() if entry.isfile()}
    assert all(member.uid == member.gid == 0 for member in members.values())
    return members, data


def build_id(elf):
    note = elf.section_data(elf.by_name['.note.gnu.build-id'])
    name_size, size, kind = struct.unpack_from(elf.order + 'III', note)
    assert kind == 3 and note[12:12 + name_size].rstrip(b'\0') == b'GNU'
    start = 12 + ((name_size + 3) & ~3)
    return note[start:start + size].hex()


def main():
    runtime, debug, development, tools, tools_debug, copyright, changelog, *models = sys.argv[1:]
    members, data = contents(runtime)
    expected_models = {'usr/share/yang/modules/libyang/' + Path(model).name: Path(model).read_bytes() for model in models}
    actual_models = {name: payload for name, payload in data.items() if name.startswith('usr/share/yang/modules/libyang/')}
    assert actual_models == expected_models
    assert data['usr/share/doc/libyang3/copyright'] == Path(copyright).read_bytes()
    assert gzip.decompress(data['usr/share/doc/libyang3/changelog.Debian.gz']) == Path(changelog).read_bytes()
    debug_members, debug_data = contents(debug)
    libraries = [name for name in data if name.endswith('/libyang.so.3.9.1')]
    assert len(libraries) == 1
    library = libraries[0]
    elf = Elf(data[library])
    assert elf.soname == 'libyang.so.3'
    assert members[library.rsplit('/', 1)[0] + '/libyang.so.3'].linkname == 'libyang.so.3.9.1'
    assert {'libpcre2-8.so.0', 'libxxhash.so.0'} <= set(elf.needed)
    assert not any(name.startswith(('pcre2_', 'XXH')) for name in elf.exports)
    identity = build_id(elf)
    debug_path = 'usr/lib/debug/.build-id/' + identity[:2] + '/' + identity[2:] + '.debug'
    symbols = debug_data[debug_path]
    symbol_elf = Elf(symbols)
    assert build_id(symbol_elf) == identity and '.debug_info' in symbol_elf.by_name
    assert '.debug_info' not in elf.by_name
    link = elf.section_data(elf.by_name['.gnu_debuglink'])
    assert link.split(b'\0', 1)[0].decode() == Path(debug_path).name
    assert struct.unpack(elf.order + 'I', link[-4:])[0] == zlib.crc32(symbols)
    dev_members, dev_data = contents(development)
    assert 'usr/include/libyang/libyang.h' in dev_data
    assert any(name.endswith('/pkgconfig/libyang.pc') for name in dev_data)
    assert any(name.endswith('/libyang.so') and item.issym() and item.linkname == 'libyang.so.3' for name, item in dev_members.items())
    assert 'usr/share/doc/libyang-dev/html/index.html' in dev_data
    tool_members, tool_data = contents(tools)
    _, tool_debug_data = contents(tools_debug)
    for tool in ('yanglint', 'yangre'):
        binary = Elf(tool_data['usr/bin/' + tool])
        assert 'libyang.so.3' in binary.needed
        identity = build_id(binary)
        symbol_path = 'usr/lib/debug/.build-id/' + identity[:2] + '/' + identity[2:] + '.debug'
        assert build_id(Elf(tool_debug_data[symbol_path])) == identity
        assert gzip.decompress(tool_data['usr/share/man/man1/' + tool + '.1.gz'])
    print('Runtime, developer, tools and build-id symbol archive contracts verified')


if __name__ == '__main__':
    main()
