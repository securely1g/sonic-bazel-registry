"""Check PI's installed ABI, Python inventory and matching debug-only TAR."""
import json
from pathlib import Path
import platform
import re
import subprocess
import sys
import tarfile
import tempfile


def output(*args):
    completed = subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    assert completed.returncode == 0, f"{args[0]} exited {completed.returncode}:\n{completed.stdout}"
    return completed.stdout


def identity(path):
    match = re.search(r"Build ID: ([0-9a-f]+)", output("readelf", "-n", str(path)))
    assert match, path
    return match[1]


def main():
    runtime, debug, configure, sdk_consumer, *deps = map(lambda x: Path(x).resolve(), sys.argv[1:])
    expected_arch = {"x86_64": "Advanced Micro Devices X86-64", "aarch64": "AArch64"}[platform.machine()]
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        for archive in [*deps, runtime, debug]:
            with tarfile.open(archive) as handle:
                handle.extractall(root, filter="data")
        with tarfile.open(runtime) as handle:
            members = {p.name.removeprefix("./"): p for p in handle if not p.isdir()}
            assert not any(p.endswith((".deb", ".a", ".la", ".pyc")) or p.startswith("usr/include/") for p in members), members
            assert "usr/lib/python3/dist-packages/google/__init__.py" not in members
            assert "usr/lib/python3/dist-packages/p4/v1/p4runtime_pb2.py" in members
            assert "usr/lib/python3/dist-packages/p4/v1/p4runtime_pb2_grpc.py" in members
            binaries = [root / p for p, member in members.items() if member.isfile() and handle.extractfile(member).read(4) == b"\x7fELF"]
            assert len(binaries) == 15, [p.name for p in binaries]
            assert all((p.uid, p.gid) == (0, 0) for p in members.values())
        with tarfile.open(debug) as handle:
            assert all(p.isdir() or p.name.removeprefix("./").startswith("usr/lib/debug/") for p in handle)
        loaders = {p.resolve() for p in root.rglob("ld-linux-*.so.*") if p.is_file()}
        assert len(loaders) == 1, loaders
        prefix = [str(loaders.pop()), "--inhibit-cache", "--library-path", ":".join(sorted({str(p.parent) for p in root.rglob("*.so*") if p.is_file()}))]
        ids = {}
        for binary in binaries:
            assert expected_arch in output("readelf", "-h", str(binary))
            assert ".debug_info" not in output("readelf", "-SW", str(binary))
            assert not re.search(r"\((?:RPATH|RUNPATH)\)", output("readelf", "-d", str(binary)))
            digest = identity(binary)
            symbols = root / "usr/lib/debug/.build-id" / digest[:2] / (digest[2:] + ".debug")
            assert symbols.is_file(), binary
            assert identity(symbols) == digest
            if binary.name == "pi_CLI_dummy":
                # Upstream links this launcher with no source objects. Its main
                # and source-level debug information belong to libpicli.so.
                assert re.search(r"\bUND\s+main\b", output("readelf", "-Ws", str(binary)))
                assert "libpicli.so.0" in output("readelf", "-d", str(binary))
            else:
                assert ".debug_info" in output("readelf", "-SW", str(symbols)), binary
            ids[binary.name] = digest
        for name in ("pi_gen_native_json", "pi_convert_p4info", "pi_CLI_dummy"):
            listing = output(*prefix, "--list", str(root / "usr/bin" / name))
            assert "not found" not in listing, listing
            assert all(Path(p).resolve().is_relative_to(root) for p in re.findall(r"=> (/\S+)", listing)), listing
        listing = output(*prefix, "--list", str(sdk_consumer))
        assert "not found" not in listing, listing
        assert all(Path(p).resolve().is_relative_to(root) for p in re.findall(r"=> (/\S+)", listing)), listing
        output(*prefix, str(sdk_consumer))
        source = root / "input.p4info.txt"
        source.write_text('actions { preamble { id: 16777217 name: "source-runtime" alias: "source_runtime" } params { id: 1 name: "port" bitwidth: 9 } }\n')
        target = root / "output.p4info.bin"
        output(*prefix, str(root / "usr/bin/pi_convert_p4info"), "-i", str(source), "-o", str(target), "-f", "prototext", "-t", "proto")
        roundtrip = root / "roundtrip.p4info.txt"
        output(*prefix, str(root / "usr/bin/pi_convert_p4info"), "-i", str(target), "-o", str(roundtrip), "-f", "proto", "-t", "prototext")
        assert 'name: "source-runtime"' in roundtrip.read_text()
        assert "bitwidth: 9" in roundtrip.read_text()
        gdb = output("gdb", "-nx", "-batch", "-ex", "set debuginfod enabled off", "-ex", "set debug-file-directory " + str(root / "usr/lib/debug"), "-ex", "file " + str(root / "usr/bin/pi_convert_p4info"), "-ex", "info line main")
        assert re.search(r"Line \d+ of .*convert_p4info", gdb), gdb
        cli_library = next(binary for binary in binaries if binary.name == "libpicli.so.0.0.0")
        cli_gdb = output("gdb", "-nx", "-batch", "-ex", "set debuginfod enabled off", "-ex", "set debug-file-directory " + str(root / "usr/lib/debug"), "-ex", "file " + str(cli_library), "-ex", "info line main")
        assert re.search(r'Line \d+ of "(?:.*/)?main\.c"', cli_gdb), cli_gdb
        log = configure.read_text()
        assert "grpc_cpp_plugin" in log and "grpc_python_plugin" in log and "protobuf" in log
        print(json.dumps({"architecture": platform.machine(), "build_ids": ids, "installed_sdk_consumer": True, "installed_p4info_conversion": True, "gdb_source_line": True, "cli_shared_library_source_line": True}, indent=2))


if __name__ == "__main__":
    main()
