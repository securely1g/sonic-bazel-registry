"""Check the installed LLDP payload and the symbols from those exact ELFs."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import tarfile
import tempfile
import zlib


ELFS = {
    "usr/sbin/lldpd": (0, 0, 0o755, "main", "main.c"),
    "usr/sbin/lldpcli": (101, 4, 0o4750, "main", "lldpcli.c"),
    "usr/lib/x86_64-linux-gnu/liblldpctl.so.4.9.1": (0, 0, 0o644, "lldpctl_new", "connection.c"),
}
LINKS = {
    "usr/share/man/man8/lldpctl.8.gz": "lldpcli.8.gz",
    "usr/sbin/lldpctl": "lldpcli",
    "usr/lib/x86_64-linux-gnu/liblldpctl.so.4": "liblldpctl.so.4.9.1",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("runtime", "debug", "configuration", "dependencies", "readelf", "objcopy"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--file", nargs=2, action="append", default=[], metavar=("INSTALLED", "SOURCE"))
    args = parser.parse_args()
    files = {name: Path(source).absolute() for name, source in args.file}
    assert len(files) == len(args.file), "duplicate expected installed path"
    configuration = args.configuration.read_text()
    for name in ("USE_SNMP", "USE_XML"):
        assert re.search(r"^#define " + name + r" 1$", configuration, re.M), name
    for name in ("ENABLE_CDP", "ENABLE_FDP", "ENABLE_EDP", "ENABLE_SONMP", "ENABLE_PRIVSEP"):
        assert re.search(r"^#define " + name + r" /\*\*/$", configuration, re.M), name
    for name, value in (("NETLINK_RECEIVE_BUFSIZE", "2097152"), ("NETLINK_MAX_RECEIVE_BUFSIZE", "4194304")):
        assert re.search(r"^#define " + name + " " + value + r"$", configuration, re.M), name
    assert '"1970-01-01T00:00:00Z"' in configuration
    assert "C compiler command is not available for reproducible builds" in configuration
    dependencies = args.dependencies.resolve()
    # Bazel's sandbox can link individual tree-artifact files to their retained
    # outputs. Resolve the declared file inventory, not just its directory.
    declared_libraries = {path.resolve() for path in dependencies.rglob("*") if path.is_file()}
    readelf, objcopy = args.readelf.absolute(), args.objcopy.absolute()
    environment = {key: value for key, value in os.environ.items() if key not in ("LD_PRELOAD", "LD_LIBRARY_PATH", "LD_AUDIT")}
    environment.update(LC_ALL="C", DEBUGINFOD_URLS="")
    with tempfile.TemporaryDirectory(prefix="lldpd-package-", dir=os.environ.get("TEST_TMPDIR")) as temporary:
        root = Path(temporary)
        installed, debug_root, empty = root / "installed", root / "symbols", root / "empty"
        for directory in (installed, debug_root, empty):
            directory.mkdir()
        with tarfile.open(args.runtime) as stream:
            members = {member.name.removeprefix("./"): member for member in stream if not member.isdir()}
            assert len(members) == len([member for member in stream.getmembers() if not member.isdir()])
            assert set(members) == set(ELFS) | set(LINKS) | set(files), sorted(set(members) ^ (set(ELFS) | set(LINKS) | set(files)))
            for name, member in members.items():
                expected = ELFS.get(name, (0, 0, 0o777 if name in LINKS else 0o755 if name == "etc/init.d/lldpd" else 0o644))
                assert (member.uid, member.gid, member.mode) == expected[:3], (name, member.uid, member.gid, oct(member.mode))
                assert member.mtime == 1672560000, name
            # Python's data filter removes setuid bits from the disposable copy.
            # The original archive metadata above is the installation contract.
            stream.extractall(installed, filter="data")
        with tarfile.open(args.debug) as stream:
            for member in stream:
                assert member.uid == member.gid == 0, member.name
                # Shared deploy/debug rules use these fixed epochs for explicit
                # entries and tar-generated parent directories, respectively.
                assert member.mtime in ({1672560000, 946699200} if member.isdir() else {1672560000}), member.name
            stream.extractall(debug_root, filter="data")
        for name, target in LINKS.items():
            assert os.readlink(installed / name) == target
        for name, source in files.items():
            payload = (installed / name).read_bytes()
            if name.endswith(".gz"):
                assert payload[:2] == b"\x1f\x8b" and payload[4:8] == b"\0" * 4, name
                payload = gzip.decompress(payload)
            assert payload == source.read_bytes(), name

        def elf(path, *options):
            return subprocess.check_output([readelf, *options, path], text=True)

        def debugger(binary, directory, symbol):
            return subprocess.run([
                "gdb", "--nx", "--nh", "--batch", "-iex", "set auto-load off",
                "-iex", "set debuginfod enabled off", "-ex", "set debug-file-directory " + str(directory),
                "-ex", "file " + str(binary), "-ex", "info line " + symbol, "-ex", "ptype " + symbol,
            ], capture_output=True, text=True, env=environment, check=False)

        checks = []
        for relative, (_, _, _, symbol, source) in ELFS.items():
            binary = installed / relative
            assert "Advanced Micro Devices X86-64" in elf(binary, "-h")
            assert re.search(r"Type:\s+DYN", elf(binary, "-h")), relative
            assert "GNU_RELRO" in elf(binary, "-lW"), relative
            dynamic = elf(binary, "-d")
            assert "BIND_NOW" in dynamic or re.search(r"FLAGS_1.*\bNOW\b", dynamic), relative
            assert not re.search(r"\((?:RUNPATH|RPATH)\)", dynamic), relative
            build_id = re.search(r"Build ID: ([0-9a-f]+)", elf(binary, "-n")).group(1)
            symbols = debug_root / "usr/lib/debug/.build-id" / build_id[:2] / (build_id[2:] + ".debug")
            assert re.search(r"Build ID: ([0-9a-f]+)", elf(symbols, "-n")).group(1) == build_id
            assert ".debug_info" not in elf(binary, "-SW")
            assert ".debug_info" in elf(symbols, "-SW")
            section = root / "debuglink.bin"
            subprocess.run([objcopy, "--dump-section", ".gnu_debuglink=" + str(section), binary, root / "inspection-copy"], check=True)
            payload = section.read_bytes()
            assert payload.split(b"\0", 1)[0].decode() == symbols.name
            assert struct.unpack("<I", payload[-4:])[0] == zlib.crc32(symbols.read_bytes()) & 0xffffffff
            positive = debugger(binary, debug_root / "usr/lib/debug", symbol)
            negative = debugger(binary, empty, symbol)
            assert positive.returncode == 0 and re.search(r'Line \d+ of ".*' + re.escape(source) + '"', positive.stdout), positive.stdout + positive.stderr
            assert "type =" in positive.stdout, positive.stdout
            assert not re.search(r"Line \d+ of", negative.stdout + negative.stderr), negative.stdout
            checks.append({"path": relative, "build_id": build_id, "sha256": hashlib.sha256(binary.read_bytes()).hexdigest(), "gdb": "source line/type with isolated negative control"})
        loader = dependencies / "usr/lib/x86_64-linux-gnu/ld-linux-x86-64.so.2"
        libraries = str(installed / "usr/lib/x86_64-linux-gnu") + ":" + str(dependencies / "usr/lib/x86_64-linux-gnu")
        loader_checks = []
        for program in ("lldpd", "lldpcli"):
            executable = installed / "usr/sbin" / program
            listing = subprocess.check_output([loader, "--list", "--inhibit-cache", "--library-path", libraries, executable], text=True, env=environment)
            assert "not found" not in listing, listing
            resolved = {}
            for name, location in re.findall(r"^\s*(\S+) => (/\S+)", listing, re.M):
                path = Path(location).resolve()
                assert path.is_relative_to(installed.resolve()) or path in declared_libraries, (name, location, listing)
                resolved[name] = str(path)
            assert "libc.so.6" in resolved, listing
            if program == "lldpcli":
                assert Path(resolved["liblldpctl.so.4"]) == (installed / "usr/lib/x86_64-linux-gnu/liblldpctl.so.4.9.1").resolve(), listing
            loader_checks.append({"program": program, "resolved": resolved})
            result = subprocess.run([loader, "--inhibit-cache", "--library-path", libraries, installed / "usr/sbin" / program, "-vv"], check=True, capture_output=True, text=True, env=environment)
            assert "1.0.16" in result.stdout + result.stderr, result
            assert "/execroot/" not in result.stdout + result.stderr
        print(json.dumps({"result": "passed", "elf_debug_pairs": checks, "payload_files": len(members), "loader_checks": loader_checks}, sort_keys=True))


if __name__ == "__main__":
    main()
