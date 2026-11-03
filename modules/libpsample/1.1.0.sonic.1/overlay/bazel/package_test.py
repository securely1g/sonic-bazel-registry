"""Exercise the installed psample CLI/library with declared netlink fixtures."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import tarfile
import tempfile
import zlib


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("runtime", "debug", "fixture", "sdk", "copyright", "readelf", "objcopy", "mnl", "manual", "metadata"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    env = {key: value for key, value in os.environ.items() if key not in ("LD_LIBRARY_PATH", "LD_PRELOAD", "LD_AUDIT")}
    env.update(LC_ALL="C", TZ="UTC", DEBUGINFOD_URLS="")
    with tempfile.TemporaryDirectory(prefix="psample-installed-", dir=os.environ.get("TEST_TMPDIR")) as temporary:
        root = Path(temporary)
        runtime, debug, empty = (root / name for name in ("runtime", "debug", "empty"))
        for directory in (runtime, debug, empty):
            directory.mkdir()
        expected = {
            "usr/bin/psample": 0o755,
            "usr/lib/x86_64-linux-gnu/libpsample.so.1.0": 0o644,
            "usr/lib/x86_64-linux-gnu/libpsample.so.1": "libpsample.so.1.0",
            "usr/lib/x86_64-linux-gnu/libpsample.so": "libpsample.so.1",
            "usr/share/man/man8/psample.8.gz": 0o644,
            "usr/share/doc/psample/copyright": 0o644,
        }
        with tarfile.open(args.runtime) as archive:
            members = {member.name.removeprefix("./"): member for member in archive if not member.isdir()}
            assert set(members) == set(expected), members
            for name, contract in expected.items():
                member = members[name]
                assert (member.uid, member.gid, member.mtime) == (0, 0, 1672560000), name
                if isinstance(contract, str):
                    assert member.issym() and member.linkname == contract, name
                else:
                    assert member.isfile() and member.mode == contract, name
            archive.extractall(runtime, filter="data")
        for source, destination in ((args.debug, debug), (args.mnl, runtime)):
            with tarfile.open(source) as archive:
                archive.extractall(destination, filter="data")
        assert (runtime / "usr/share/doc/psample/copyright").read_bytes() == args.copyright.read_bytes()
        manual = (runtime / "usr/share/man/man8/psample.8.gz").read_bytes()
        assert manual[3] == 0 and manual[4:8] == b"\0" * 4, "gzip filename/timestamp must be omitted"
        assert gzip.decompress(manual) == args.manual.read_bytes()
        metadata = json.loads(args.metadata.read_text())
        assert metadata["schema"] == 1 and metadata["architecture"] == "amd64"
        assert set(metadata["packages"]) == {"psample"}
        fields = metadata["packages"]["psample"]["control_fields"]
        assert fields["Package"] == "psample" and fields["Version"] == "1.1-1"
        assert "libmnl0" in fields["Depends"] and "libc6" in fields["Depends"]
        library_dir = runtime / "usr/lib/x86_64-linux-gnu"
        env["LD_LIBRARY_PATH"] = str(library_dir)
        binary = runtime / "usr/bin/psample"
        library = library_dir / "libpsample.so.1.0"
        assert (library_dir / "libpsample.so").resolve() == library
        build_ids = {}

        def elf(path, *flags):
            # Inspection tools carry their own declared runtime; do not inject target libraries.
            inspection_env = {key: value for key, value in env.items() if key != "LD_LIBRARY_PATH"}
            return subprocess.check_output([args.readelf.absolute(), *flags, path], text=True, env=inspection_env)

        for installed, function, needed in ((binary, "main", {"libpsample.so.1", "libc.so.6"}),
                                            (library, "psample_dispatch", {"libmnl.so.0", "libc.so.6"})):
            assert "Advanced Micro Devices X86-64" in elf(installed, "-h")
            dynamic = elf(installed, "-d")
            assert set(re.findall(r"\(NEEDED\).*\[(.*?)\]", dynamic)) == needed, dynamic
            assert not re.search(r"\((?:RPATH|RUNPATH)\)", dynamic), dynamic
            if installed == library:
                assert "Library soname: [libpsample.so.1]" in dynamic
            build_id = re.search(r"Build ID: ([0-9a-f]+)", elf(installed, "-n")).group(1)
            build_ids[installed.name] = build_id
            symbols = debug / "usr/lib/debug/.build-id" / build_id[:2] / (build_id[2:] + ".debug")
            assert re.search(r"Build ID: ([0-9a-f]+)", elf(symbols, "-n")).group(1) == build_id
            assert ".debug_info" not in elf(installed, "-SW") and ".debug_info" in elf(symbols, "-SW")
            section = root / "debuglink.bin"
            inspection_env = {key: value for key, value in env.items() if key != "LD_LIBRARY_PATH"}
            subprocess.run([args.objcopy.absolute(), "--dump-section", ".gnu_debuglink=" + str(section), installed, root / "inspection-copy"], check=True, env=inspection_env)
            link = section.read_bytes()
            assert link.split(b"\0", 1)[0].decode() == symbols.name
            assert struct.unpack("<I", link[-4:])[0] == zlib.crc32(symbols.read_bytes()) & 0xffffffff
            for directory, present in ((debug / "usr/lib/debug", True), (empty, False)):
                result = subprocess.run(["gdb", "--nx", "--nh", "--batch", "-iex", "set auto-load off",
                    "-iex", "set debuginfod enabled off", "-ex", "set debug-file-directory " + str(directory),
                    "-ex", "file " + str(installed), "-ex", "info line " + function, "-ex", "ptype " + function],
                    capture_output=True, text=True, env=inspection_env)
                assert bool(re.search(r'Line \d+ of ".*psample.c"', result.stdout)) == present, result.stdout + result.stderr
                if present:
                    assert result.returncode == 0 and "type =" in result.stdout
        # Copy the linked SDK consumer away from Bazel's library symlinks, then use installed libpsample.
        sdk = root / "sdk-probe"
        shutil.copy2(args.sdk, sdk)
        subprocess.run([sdk], check=True, env=env, timeout=10)
        help_result = subprocess.run([binary, "--help"], capture_output=True, text=True, env=env, check=True, timeout=10)
        assert "Tool for monitoring psample packets" in help_result.stdout
        fixture_env = dict(env, LD_PRELOAD=str(args.fixture.absolute()))
        result = subprocess.run([binary, "--verbose"], capture_output=True, text=True, env=fixture_env, check=True, timeout=10)
        for expected_text in ("group 7 in-ifindex 11 out-ifindex 12 origsize 64 sample-rate 1000 seq 42",
                              "data len 9", "00 01 02 03 53 4f 4e 69 43", "SONiC",
                              "created group 7 with current seq 43", "deleted group 7 with current seq 44"):
            assert expected_text in result.stdout, result.stdout + result.stderr
        sample_only = subprocess.run([binary, "--no-config"], capture_output=True, text=True, env=fixture_env, check=True, timeout=10).stdout
        assert "sample-rate 1000" in sample_only and "created" not in sample_only and "deleted" not in sample_only
        config_only = subprocess.run([binary, "--no-sample"], capture_output=True, text=True, env=fixture_env, check=True, timeout=10).stdout
        assert "sample-rate" not in config_only and "created group 7" in config_only and "deleted group 7" in config_only
        listed = subprocess.run([binary, "--list-groups"], capture_output=True, text=True, env=fixture_env, check=True, timeout=10).stdout
        assert re.search(r"(?m)^7\s+2\s+42\s*$", listed), listed
        unavailable = subprocess.run([binary], capture_output=True, text=True, env=dict(fixture_env, PSAMPLE_FIXTURE_OPEN_FAIL="1"), timeout=10)
        assert unavailable.returncode != 0 and "Could not open netlink socket" in unavailable.stderr
        evidence = {"status": "passed", "build_ids": build_ids,
                    "runtime_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (binary, library)},
                    "sample": {"group": 7, "iif": 11, "oif": 12, "original_size": 64, "rate": 1000, "sequence": 42, "payload_hex": "00010203534f4e6943"},
                    "config": ["new_group:7:43", "del_group:7:44"], "open_failure": "rejected",
                    "sdk": "linked header consumer uses installed library", "gdb": "both ELFs, source/type and negative control",
                    "scope": "installed CLI and library parser with declared kernel-transport fixture; no live kernel/ASIC sampling claim"}
        print(json.dumps(evidence, sort_keys=True))
        if os.environ.get("TEST_UNDECLARED_OUTPUTS_DIR"):
            (Path(os.environ["TEST_UNDECLARED_OUTPUTS_DIR"]) / "installed-psample.json").write_text(json.dumps(evidence, indent=2) + "\n")


if __name__ == "__main__":
    main()
