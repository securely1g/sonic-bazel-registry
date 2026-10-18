"""Exercise installed programs and their matching detached debug symbols."""

import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import tarfile
import tempfile
import zlib


def command(*arguments, **kwargs):
    return subprocess.check_output(arguments, text=True, stderr=subprocess.STDOUT, **kwargs)


def build_id(path):
    found = re.search(r"Build ID: ([0-9a-f]+)", command("readelf", "-n", str(path)))
    assert found, path
    return found.group(1)


def main():
    runtime, debug, source, configure_log, *dependencies = [Path(value).resolve() for value in sys.argv[1:]]
    with tempfile.TemporaryDirectory(dir=os.environ["TEST_TMPDIR"]) as temporary:
        root = Path(temporary)
        for archive in [*dependencies, runtime]:
            with tarfile.open(archive) as package:
                package.extractall(root, filter="data")
        with tarfile.open(runtime) as package:
            files = {member.name: member for member in package.getmembers() if not member.isdir()}
            for member in files.values():
                assert (member.uid, member.gid) == (0, 0), member.name
            for name in ("socat1", "filan", "procan", "socat-chain.sh", "socat-mux.sh", "socat-broker.sh"):
                assert files["usr/bin/" + name].mode == 0o755, name
        assert os.readlink(root / "usr/bin/socat") == "socat1"
        for name in ("socat-chain.sh", "socat-mux.sh", "socat-broker.sh"):
            assert (root / "usr/bin" / name).read_bytes() == (source.parent.parent / name).read_bytes()
        assert (root / "usr/share/man/man1/socat1.1").read_bytes() == source.read_bytes()
        for name in ("socat", "filan", "procan"):
            assert (root / "usr/share/man/man1" / (name + ".1")).resolve() == root / "usr/share/man/man1/socat1.1"
        assert (root / "usr/share/doc/socat/COPYING").read_bytes() == (source.parent.parent / "COPYING").read_bytes()
        assert (root / "usr/share/doc/socat/copyright").read_bytes() == (source.parent.parent / "copyright").read_bytes()

        loaders = {path.resolve() for path in root.rglob("ld-linux-*.so.*") if path.is_file()}
        assert len(loaders) == 1, loaders
        loader = str(loaders.pop())
        libraries = sorted({str(path.parent) for path in root.rglob("*.so*") if path.is_file()})
        environment = dict(os.environ)
        for key in ("LD_PRELOAD", "LD_LIBRARY_PATH", "LD_AUDIT"):
            environment.pop(key, None)
        prefix = [loader, "--inhibit-cache", "--library-path", os.pathsep.join(libraries)]
        expected_sources = {"socat1": "socat.c", "filan": "filan_main.c", "procan": "procan_main.c"}

        def debugger(binary):
            return subprocess.run(["gdb", "-nx", "-batch", "-ex", "set debuginfod enabled off",
                                   "-ex", f"set debug-file-directory {root}/usr/lib/debug", "-ex",
                                   f"file {binary}", "-ex", "info line main"], text=True,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout

        identities = {}
        for name in expected_sources:
            binary = root / "usr/bin" / name
            listing = command(*prefix, "--list", str(binary), env=environment)
            assert "not found" not in listing, listing
            resolved = re.findall(r"=> (/\S+)", listing)
            assert resolved, listing
            assert all(Path(path).resolve().is_relative_to(root) for path in resolved), listing
            dynamic = command("readelf", "-d", str(binary))
            assert not re.search(r"\((?:RPATH|RUNPATH)\)", dynamic), dynamic
            assert ".debug_info" not in command("readelf", "-SW", str(binary))
            assert not re.search(r"Line \d+ of", debugger(binary))
            identities[name] = build_id(binary)

        version = command(*prefix, str(root / "usr/bin/socat1"), "-V", env=environment)
        assert "socat version 1.8.0.2" in version, version
        for feature in ("WITH_OPENSSL", "WITH_READLINE", "WITH_LIBWRAP"):
            assert re.search(r"#define " + feature + r" 1\b", version), (
                version + "\n" + "\n".join(line for line in configure_log.read_text().splitlines()
                                            if "error:" in line or "checked for openssl/ssl.h" in line))
        payload = "installed socat preserves stdin/stdout\n"
        assert command(*prefix, str(root / "usr/bin/socat1"), "-u", "STDIN", "STDOUT",
                       input=payload, env=environment) == payload
        for name in ("filan", "procan"):
            assert command(*prefix, str(root / "usr/bin" / name), "-h", env=environment)

        with tarfile.open(debug) as package:
            package.extractall(root, filter="data")
        for name, identity in identities.items():
            binary = root / "usr/bin" / name
            symbols = root / "usr/lib/debug/.build-id" / identity[:2] / (identity[2:] + ".debug")
            assert build_id(symbols) == identity
            assert ".debug_info" in command("readelf", "-SW", str(symbols))
            section = root / (name + ".debuglink")
            command("objcopy", "--dump-section", f".gnu_debuglink={section}",
                    str(binary), str(root / (name + ".copy")))
            contents = section.read_bytes()
            assert contents.split(b"\0", 1)[0].decode() == symbols.name
            assert struct.unpack("<I", contents[-4:])[0] == zlib.crc32(symbols.read_bytes())
            location = debugger(binary)
            assert re.search(r'Line \d+ of .*' + re.escape(expected_sources[name]), location), location
        print(version)
        print("Installed three programs, declared library closure, stdin/stdout transfer, feature parity and debug symbols passed")


if __name__ == "__main__":
    main()
