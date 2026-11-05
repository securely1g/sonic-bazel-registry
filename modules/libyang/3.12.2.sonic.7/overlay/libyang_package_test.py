"""Check Debian install contracts using archive data, declared ELF metadata, and GDB."""
import gzip
import hashlib
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


def check_permissions(members, executables=()):
    # Debian dh_fixperms installs documentation/headers as 0644 and tools as 0755.
    for name, member in members.items():
        if member.isfile():
            expected = 0o755 if name in executables else 0o644
            assert member.mode == expected, (name, oct(member.mode), oct(expected))
        elif member.isdir():
            assert member.mode == 0o755, (name, oct(member.mode))


def verify_gdb_source_line(runtime_tar, debug_tar, library_relpath):
    with tempfile.TemporaryDirectory(prefix='libyang-symbols-') as temporary:
        root = Path(temporary)
        runtime_dir = root / 'runtime'
        symbols_dir = root / 'symbols'
        runtime_dir.mkdir()
        symbols_dir.mkdir()
        with tarfile.open(runtime_tar) as source:
            source.extractall(runtime_dir, filter='data')
        with tarfile.open(debug_tar) as source:
            source.extractall(symbols_dir, filter='data')
        library_file = runtime_dir / library_relpath
        result = subprocess.run(
            [
                'gdb', '-nx', '-batch',
                '-iex', 'set auto-load off',
                '-ex', 'set debuginfod enabled off',
                '-ex', f'set debug-file-directory {symbols_dir}/usr/lib/debug',
                '-ex', f'file {library_file}',
                '-ex', 'info line ly_ctx_new',
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=dict(os.environ, LC_ALL='C'),
            timeout=60,
        )
        print(result.stdout, end='')
        assert result.returncode == 0 and re.search(r'Line [0-9]+ of .*context\.c', result.stdout), result.stdout
        if os.environ.get('TEST_UNDECLARED_OUTPUTS_DIR'):
            receipt = {
                'runtime_tar_sha256': hashlib.sha256(Path(runtime_tar).read_bytes()).hexdigest(),
                'debug_tar_sha256': hashlib.sha256(Path(debug_tar).read_bytes()).hexdigest(),
                'runtime_sha256': hashlib.sha256(library_file.read_bytes()).hexdigest(),
                'line_lookup': result.stdout.strip(),
            }
            out_dir = Path(os.environ['TEST_UNDECLARED_OUTPUTS_DIR'])
            (out_dir / 'libyang-installed-debug.json').write_text(json.dumps(receipt, indent=2) + '\n')


def main():
    runtime, debug, development, tools, tools_debug, copyright, changelog, *models = sys.argv[1:]
    members, data = contents(runtime)
    check_permissions(members)
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
    verify_gdb_source_line(runtime, debug, library)
    dev_members, dev_data = contents(development)
    check_permissions(dev_members)
    assert 'usr/include/libyang/libyang.h' in dev_data
    assert any(name.endswith('/pkgconfig/libyang.pc') for name in dev_data)
    assert any(name.endswith('/libyang.so') and item.issym() and item.linkname == 'libyang.so.3' for name, item in dev_members.items())
    assert 'usr/share/doc/libyang-dev/html/index.html' in dev_data
    tool_members, tool_data = contents(tools)
    check_permissions(tool_members, ('usr/bin/yanglint', 'usr/bin/yangre'))
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
