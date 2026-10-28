"""Check original Debian feature/ABI requirements on target ELF without execution.

Sources: debian/rules configure options and libnl build dependency, LIBCURRENT
42/LIBAGE 2/LIBREVISION 0, and original target Perl 5.36 development packages.
This catches successful configure exits that silently disable required features.
"""
import argparse
import re
from pathlib import Path
from elf_metadata import Elf


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--machine', type=int, required=True)
    parser.add_argument('--header', required=True)
    parser.add_argument('--library', action='append', default=[])
    args = parser.parse_args()
    header = Path(args.header).read_text(encoding='latin1')
    for macro in ['HAVE_LIBNL3', 'HAVE_NETLINK_NETLINK_H', 'NETSNMP_EMBEDDED_PERL', 'NETSNMP_USE_MYSQL', 'HAVE_CURSES_H']:
        assert re.search(r'^#define ' + macro + r' 1$', header, re.MULTILINE), macro
    required = {
        "snmp": {"libssl.so.3", "libcrypto.so.3"},
        'netsnmp': {'libssl.so.3', 'libcrypto.so.3'},
        'netsnmpagent': {'libnetsnmp.so.40', 'libperl.so.5.36', 'libwrap.so.0'},
        'netsnmpmibs': {'libnetsnmpagent.so.40', 'libnl-3.so.200', 'libsensors.so.5', 'libpci.so.3'},
        'netsnmphelpers': set(),
        'netsnmptrapd': {'libnetsnmpmibs.so.40', 'libmariadb.so.3'},
    }
    exports = {}
    for value in args.library:
        name, location = value.split('=', 1)
        elf = Elf(Path(location).read_bytes())
        assert elf.machine == args.machine, (name, elf.machine, args.machine)
        assert elf.soname == 'lib' + name + '.so.40', (name, elf.soname)
        assert required[name].issubset(elf.needed), (name, required[name], elf.needed)
        assert elf.build_id, name
        exports[name] = elf.exports
        # LIBNL is a separate native shared producer, not statically embedded.
        if name == 'netsnmpmibs':
            assert 'nl_connect' not in elf.exports
    assert exports['snmp'] == exports['netsnmp'], 'original compatibility library reuses the same TOBJS public API'


if __name__ == '__main__':
    main()
