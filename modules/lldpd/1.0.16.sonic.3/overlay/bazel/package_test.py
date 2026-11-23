"""Verify the Debian installation, native ABI, and exact debug-symbol pairs."""
import argparse
import gzip
import json
import os
from pathlib import Path
import platform
import re
import struct
import subprocess
import tarfile
import tempfile
import zlib


def extract(archive, root):
    root.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive) as stream:
        # The fixed APT archives contain target-root absolute symlinks. Resolve
        # these inside the disposable target root, never against the host.
        for member in stream:
            if member.issym() and member.linkname.startswith("/"):
                parent = Path(member.name).parent
                member.linkname = os.path.relpath(member.linkname.lstrip("/"), parent)
            stream.extract(member, root, filter="data")


def run(command, **kwargs):
    return subprocess.check_output([str(x) for x in command], text=True, **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("runtime", "debug", "development", "configuration", "dependencies", "readelf", "objcopy", "consumer"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--architecture", choices=["amd64", "arm64"], required=True)
    parser.add_argument("--file", nargs=2, action="append", default=[])
    args = parser.parse_args()
    triplet, machine = {"amd64": ("x86_64-linux-gnu", "Advanced Micro Devices X86-64"), "arm64": ("aarch64-linux-gnu", "AArch64")}[args.architecture]
    elfs = {"usr/sbin/lldpd": (0, 0, 0o755), "usr/sbin/lldpcli": (101, 4, 0o4750), "usr/lib/" + triplet + "/liblldpctl.so.4.9.1": (0, 0, 0o644)}
    links = {"usr/sbin/lldpctl": "lldpcli", "usr/share/man/man8/lldpctl.8.gz": "lldpcli.8.gz", "usr/lib/" + triplet + "/liblldpctl.so.4": "liblldpctl.so.4.9.1"}
    files = {name: Path(source) for name, source in args.file}
    configuration = args.configuration.read_text()
    for name in ("USE_SNMP", "USE_XML"):
        assert re.search(r"^#define " + name + r" 1$", configuration, re.M), name
    for name in ("ENABLE_CDP", "ENABLE_FDP", "ENABLE_EDP", "ENABLE_SONMP", "ENABLE_PRIVSEP"):
        assert re.search(r"^#define " + name + r" /\*\*/$", configuration, re.M), name
    for name, value in (("NETLINK_RECEIVE_BUFSIZE", "2097152"), ("NETLINK_MAX_RECEIVE_BUFSIZE", "4194304")):
        assert re.search(r"^#define " + name + " " + value + r"$", configuration, re.M), name
    with tempfile.TemporaryDirectory(dir=os.environ.get("TEST_TMPDIR")) as temporary:
        root = Path(temporary)
        installed, symbols, dependencies = root / "installed", root / "symbols", root / "dependencies"
        with tarfile.open(args.runtime) as stream:
            members = {member.name.removeprefix("./"): member for member in stream if not member.isdir()}
            assert set(members) == set(elfs) | set(links) | set(files), sorted(set(members) ^ (set(elfs) | set(links) | set(files)))
            for name, member in members.items():
                expected = elfs.get(name, (0, 0, 0o777 if name in links else 0o755 if name == "etc/init.d/lldpd" else 0o644))
                assert (member.uid, member.gid, member.mode) == expected, name
        extract(args.runtime, installed)
        extract(args.debug, symbols)
        for name, target in links.items():
            assert os.readlink(installed / name) == target
        for name, source in files.items():
            content = (installed / name).read_bytes()
            if name.endswith(".gz"):
                assert content[4:8] == b"\0" * 4, name
                content = gzip.decompress(content)
            assert content == source.read_bytes(), name
        with tarfile.open(args.development) as stream:
            development = {item.name.removeprefix("./"): item for item in stream if not item.isdir()}
            assert set(development) == {"usr/include/lldpctl.h", "usr/include/lldp-const.h", "usr/lib/" + triplet + "/liblldpctl.so", "usr/lib/" + triplet + "/pkgconfig/lldpctl.pc"}
            assert development["usr/lib/" + triplet + "/liblldpctl.so"].linkname == "liblldpctl.so.4"
        pairs = []
        for name in elfs:
            binary = installed / name
            header = run([args.readelf, "-h", binary])
            assert machine in header and re.search(r"Type:\s+DYN", header), header
            assert "GNU_RELRO" in run([args.readelf, "-lW", binary]), name
            dynamic = run([args.readelf, "-d", binary])
            assert "BIND_NOW" in dynamic or re.search(r"FLAGS_1.*\bNOW\b", dynamic), name
            assert not re.search(r"\((?:RUNPATH|RPATH)\)", dynamic), dynamic
            if "liblldpctl.so" in name:
                assert "Library soname: [liblldpctl.so.4]" in dynamic, dynamic
                exports = run([args.readelf, "--dyn-syms", "-W", binary])
                assert "lldpctl_new" in exports and "init_atom_builder" not in exports
            if name.endswith("lldpcli"):
                assert "Shared library: [liblldpctl.so.4]" in dynamic
            build_id = re.search(r"Build ID: ([0-9a-f]+)", run([args.readelf, "-n", binary])).group(1)
            debug = symbols / "usr/lib/debug/.build-id" / build_id[:2] / (build_id[2:] + ".debug")
            assert build_id in run([args.readelf, "-n", debug])
            assert ".debug_info" not in run([args.readelf, "-SW", binary])
            assert ".debug_info" in run([args.readelf, "-SW", debug])
            assert "DW_TAG_compile_unit" in run([args.readelf, "--debug-dump=info", debug])
            section = root / "debuglink"
            subprocess.run([str(args.objcopy), "--dump-section", ".gnu_debuglink=" + str(section), str(binary), str(root / "inspection-copy")], check=True)
            content = section.read_bytes()
            assert content.split(b"\0", 1)[0].decode() == debug.name
            assert struct.unpack("<I", content[-4:])[0] == zlib.crc32(debug.read_bytes()) & 0xffffffff
            pairs.append(build_id)
        native = platform.machine() in ({"x86_64", "amd64"} if args.architecture == "amd64" else {"aarch64", "arm64"})
        if native:
            extract(args.dependencies, dependencies)
            loader = dependencies / "usr/lib" / triplet / ("ld-linux-x86-64.so.2" if args.architecture == "amd64" else "ld-linux-aarch64.so.1")
            libraries = str(installed / "usr/lib" / triplet) + ":" + str(dependencies / "usr/lib" / triplet)
            for program in ("lldpd", "lldpcli"):
                command = [loader, "--inhibit-cache", "--library-path", libraries, installed / "usr/sbin" / program]
                listing = run(command[:1] + ["--list"] + command[1:])
                assert "not found" not in listing, listing
                for location in re.findall(r"=> (/\S+)", listing):
                    path = Path(location).resolve()
                    assert path.is_relative_to(installed) or path.is_relative_to(dependencies), location
                assert "1.0.16" in run(command + ["-vv"], stderr=subprocess.STDOUT)
            run([loader, "--inhibit-cache", "--library-path", libraries, args.consumer])
        print(json.dumps({"architecture": args.architecture, "elf_debug_pairs": pairs, "runtime": "PASS" if native else "NOT_RUN: cross compilation"}))


if __name__ == "__main__":
    main()
