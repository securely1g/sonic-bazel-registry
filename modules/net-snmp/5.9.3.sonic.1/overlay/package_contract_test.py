"""Check the delivered Net-SNMP executable/library inventory and symbol pairs.

The upstream apps/Makefile.in enables snmppcap whenever the declared libpcap
headers and library are available; this applies to both supported CPUs.
"""
import argparse
from pathlib import PurePosixPath
import tarfile
import zlib

from elf_metadata import Elf


PROGRAMS = (
    "agentxtrap", "encode_keychange", "snmpbulkget", "snmpbulkwalk", "snmpdelta",
    "snmpdf", "snmpget", "snmpgetnext", "snmpnetstat", "snmppcap", "snmpping",
    "snmpps", "snmpset", "snmpstatus", "snmptable", "snmptest", "snmptls",
    "snmptranslate", "snmptrap", "snmpusm", "snmpvacm", "snmpwalk",
)
LIBRARIES = ("snmp", "netsnmp", "netsnmpagent", "netsnmphelpers", "netsnmpmibs")
PERL_MODULES = (
    "NetSNMP/ASN/ASN", "NetSNMP/OID/OID", "NetSNMP/default_store/default_store",
    "NetSNMP/agent/agent", "NetSNMP/agent/default_store/default_store",
    "NetSNMP/TrapReceiver/TrapReceiver", "SNMP/SNMP",
)


def contents(path):
    files = {}
    with tarfile.open(path) as archive:
        for member in archive:
            if member.isdir():
                continue
            name = member.name.removeprefix("./")
            assert name not in files, ("duplicate archive member", name)
            files[name] = (member, archive.extractfile(member).read() if member.isfile() else None)
    return files


def check(machine, runtime, debug):
    assert machine in (62, 183), machine
    multiarch = "x86_64-linux-gnu" if machine == 62 else "aarch64-linux-gnu"
    libdir = "usr/lib/" + multiarch + "/"
    expected = {
        "snmp": {"usr/bin/" + name for name in PROGRAMS},
        "snmpd": {"usr/sbin/snmpd"},
        "snmptrapd": {"usr/sbin/snmptrapd"},
        "libsnmp40": {libdir + "lib" + name + ".so.40.2.0" for name in LIBRARIES},
        "libnetsnmptrapd40": {libdir + "libnetsnmptrapd.so.40.2.0"},
        "libsnmp-perl": {libdir + "perl5/5.36/auto/" + name + ".so" for name in PERL_MODULES},
    }
    assert set(runtime) == set(debug) == set(expected), (runtime.keys(), debug.keys())
    checked = 0
    for group, paths in expected.items():
        files, symbols = contents(runtime[group]), contents(debug[group])
        elfs = {name for name, (_, payload) in files.items() if payload and payload.startswith(b"\x7fELF")}
        assert elfs == paths, (group, "missing or extra ELF files", elfs ^ paths)
        if group == "snmp":
            link, _ = files["usr/bin/snmpinform"]
            assert link.issym() and link.linkname == "snmptrap" and link.uid == link.gid == 0, "snmpinform"
        for name in sorted(paths):
            member, payload = files[name]
            mode = 0o755 if name.startswith(("usr/bin/", "usr/sbin/")) else 0o644
            assert member.isfile() and member.mode == mode and member.uid == member.gid == 0, name
            elf = Elf(payload)
            assert elf.machine == machine and elf.build_id, (name, elf.machine, machine)
            debug_path = "usr/lib/debug/.build-id/" + elf.build_id[:2] + "/" + elf.build_id[2:] + ".debug"
            assert debug_path in symbols, (name, "missing matching debug file", debug_path)
            debug_member, debug_payload = symbols[debug_path]
            assert debug_member.isfile() and debug_member.uid == debug_member.gid == 0, debug_path
            debug_elf = Elf(debug_payload)
            assert debug_elf.machine == machine and debug_elf.build_id == elf.build_id, name
            assert elf.debuglink == PurePosixPath(debug_path).name, (name, "wrong debug link")
            assert elf.debuglink_crc == zlib.crc32(debug_payload), (name, "wrong debug CRC")
            for section in (".debug_info", ".debug_line"):
                assert section not in elf.by_name, (name, "unstripped runtime", section)
                assert section in debug_elf.by_name, (name, "missing debug information", section)
            if group in ("libsnmp40", "libnetsnmptrapd40"):
                soname = PurePosixPath(name).name.removesuffix(".2.0")
                assert elf.soname == soname, (name, elf.soname)
                link, _ = files[libdir + soname]
                assert link.issym() and link.linkname == PurePosixPath(name).name, name
            checked += 1
    assert checked == 37, checked
    return checked


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--machine", type=int, required=True)
    parser.add_argument("--runtime", action="append", required=True)
    parser.add_argument("--debug", action="append", required=True)
    args = parser.parse_args()
    count = check(args.machine, dict(value.split("=", 1) for value in args.runtime),
                  dict(value.split("=", 1) for value in args.debug))
    print(f"Verified all {count} installed Net-SNMP ELF files and matching debug payloads")


if __name__ == "__main__":
    main()
