"""Exercise installed SONiC sflowtool decoding, forwarding and matching symbols."""
import argparse
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import socket
import struct
import subprocess
import tarfile
import tempfile
import zlib


def datagram(agent):
    """An sFlow v5 interface-counter sample, following upstream sflow.h."""
    address = ipaddress.ip_address(agent)
    header = struct.pack("!II", 5, 1 if address.version == 4 else 2) + address.packed
    header += struct.pack("!IIII", 0, 42, 123000, 1)
    counters = struct.pack("!IIQIIQ6IQ6I", 7, 6, 1000000000, 1, 3, 123456,
                           11, 12, 13, 14, 15, 16, 654321, 21, 22, 23, 24, 25, 0)
    sample = struct.pack("!IIIII", 1, 7, 1, 1, len(counters)) + counters
    return header + struct.pack("!II", 2, len(sample)) + sample


def pcap(payloads):
    """Ethernet/IPv4/UDP capture of the independent protocol fixtures."""
    result = struct.pack("<IHHIIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1)
    for payload in payloads:
        udp = struct.pack("!HHHH", 6343, 6343, 8 + len(payload), 0) + payload
        ip = struct.pack("!BBHHHBBH4s4s", 0x45, 0, 20 + len(udp), 1, 0, 64, 17, 0,
                         socket.inet_aton("192.0.2.1"), socket.inet_aton("127.0.0.1"))
        packet = b"\x02\0\0\0\0\x01\x02\0\0\0\0\x02\x08\0" + ip + udp
        result += struct.pack("<IIII", 1700000000, 12345, len(packet), len(packet)) + packet
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("runtime", "debug", "unstripped", "copyright", "readelf", "objcopy"):
        parser.add_argument("--" + key, type=Path, required=True)
    args = parser.parse_args()
    env = {key: value for key, value in os.environ.items() if key not in ("LD_LIBRARY_PATH", "LD_PRELOAD", "LD_AUDIT")}
    env.update(LC_ALL="C", TZ="UTC", DEBUGINFOD_URLS="")
    with tempfile.TemporaryDirectory(prefix="sflowtool-installed-", dir=os.environ.get("TEST_TMPDIR")) as temporary:
        root = Path(temporary)
        runtime, debug, empty = (root / name for name in ("runtime", "debug", "empty"))
        for path in (runtime, debug, empty):
            path.mkdir()
        with tarfile.open(args.runtime) as archive:
            members = {member.name.removeprefix("./"): member for member in archive if not member.isdir()}
            assert set(members) == {"usr/bin/sflowtool", "usr/share/doc/sflowtool/copyright"}, members
            for name, member in members.items():
                assert member.isfile() and (member.uid, member.gid, member.mtime) == (0, 0, 1672560000), name
                assert member.mode == (0o755 if name == "usr/bin/sflowtool" else 0o644), name
            archive.extractall(runtime, filter="data")
        with tarfile.open(args.debug) as archive:
            archive.extractall(debug, filter="data")
        assert (runtime / "usr/share/doc/sflowtool/copyright").read_bytes() == args.copyright.read_bytes()
        binary = runtime / "usr/bin/sflowtool"

        def elf(path, *flags):
            return subprocess.check_output([args.readelf.absolute(), *flags, path], text=True, env=env)

        assert "Advanced Micro Devices X86-64" in elf(binary, "-h")
        dynamic = elf(binary, "-d")
        assert set(re.findall(r"\(NEEDED\).*\[(.*?)\]", dynamic)) == {"libc.so.6"}, dynamic
        assert not re.search(r"\((?:RPATH|RUNPATH)\)", dynamic), dynamic
        build_id = re.search(r"Build ID: ([0-9a-f]+)", elf(binary, "-n")).group(1)
        symbols = debug / "usr/lib/debug/.build-id" / build_id[:2] / (build_id[2:] + ".debug")
        assert re.search(r"Build ID: ([0-9a-f]+)", elf(symbols, "-n")).group(1) == build_id
        assert re.search(r"Build ID: ([0-9a-f]+)", elf(args.unstripped, "-n")).group(1) == build_id
        assert ".debug_info" not in elf(binary, "-SW")
        assert ".debug_info" in elf(symbols, "-SW") and ".debug_info" in elf(args.unstripped, "-SW")
        section = root / "debuglink.bin"
        subprocess.run([args.objcopy.absolute(), "--dump-section", ".gnu_debuglink=" + str(section), binary, root / "inspection-copy"], check=True, env=env)
        link = section.read_bytes()
        assert link.split(b"\0", 1)[0].decode() == symbols.name
        assert struct.unpack("<I", link[-4:])[0] == zlib.crc32(symbols.read_bytes()) & 0xffffffff
        for directory, expected in ((debug / "usr/lib/debug", True), (empty, False)):
            result = subprocess.run(["gdb", "--nx", "--nh", "--batch", "-iex", "set auto-load off",
                                     "-iex", "set debuginfod enabled off", "-ex", "set debug-file-directory " + str(directory),
                                     "-ex", "file " + str(binary), "-ex", "info line main", "-ex", "ptype main"],
                                    capture_output=True, text=True, env=env, check=False)
            found = bool(re.search(r'Line \d+ of ".*sflowtool.c"', result.stdout))
            assert found == expected, result.stdout + result.stderr
            if expected:
                assert result.returncode == 0 and "type =" in result.stdout
        help_result = subprocess.run([binary, "-h"], capture_output=True, text=True, env=env, timeout=10)
        assert "version: 6.11" in help_result.stdout + help_result.stderr

        agents = ("192.0.2.7", "2001:db8::7")
        packets = [datagram(agent) for agent in agents]
        capture = root / "counters.pcap"
        capture.write_bytes(pcap(packets))
        result = subprocess.run([binary, "-j", "-r", capture], capture_output=True, text=True, env=env, check=True, timeout=10)
        decoded = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
        assert len(decoded) == 2, result.stdout
        for row, agent in zip(decoded, agents):
            assert ipaddress.ip_address(row["agent"]) == ipaddress.ip_address(agent) and int(row["datagramVersion"]) == 5, row
            assert int(row["packetSequenceNo"]) == 42, row
            sample = row["samples"][0]
            counter = sample["elements"][0]
            for name, value in {"ifIndex": 7, "ifSpeed": 1000000000, "ifInOctets": 123456, "ifOutOctets": 654321, "ifInUcastPkts": 11}.items():
                assert int(counter[name]) == value, (name, counter)
        # Exercise the same binary's forwarding mode without a daemon or privileges.
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as collector:
            collector.bind(("127.0.0.1", 0))
            collector.settimeout(5)
            subprocess.run([binary, "-r", capture, "-f", "127.0.0.1/" + str(collector.getsockname()[1])],
                           capture_output=True, text=True, env=env, check=True, timeout=10)
            assert [collector.recvfrom(65535)[0] for _ in packets] == packets
        malformed = root / "unsupported-version.pcap"
        malformed.write_bytes(pcap([struct.pack("!I", 99) + packets[0][4:]]))
        rejected = subprocess.run([binary, "-j", "-r", malformed], capture_output=True, text=True, env=env, timeout=10)
        assert "unexpected datagram version" in rejected.stderr, rejected.stdout + rejected.stderr
        evidence = {"status": "passed", "build_id": build_id, "runtime_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
                    "agents": agents, "counter_fields": ["ifIndex", "ifSpeed", "ifInOctets", "ifOutOctets", "ifInUcastPkts"],
                    "forwarded_datagrams": 2, "unsupported_version": "rejected", "gdb": "source/type with negative control"}
        print(json.dumps(evidence, sort_keys=True))
        if os.environ.get("TEST_UNDECLARED_OUTPUTS_DIR"):
            (Path(os.environ["TEST_UNDECLARED_OUTPUTS_DIR"]) / "installed-sflowtool.json").write_text(json.dumps(evidence, indent=2) + "\n")


if __name__ == "__main__":
    main()
