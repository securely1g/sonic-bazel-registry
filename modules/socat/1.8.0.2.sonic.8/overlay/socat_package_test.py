"""Exercise the installed Debian payload and public program behavior.

Contract: Makefile.in install, debian/docs/examples/links and debhelper 13
installation/compression rules; socat's documented STDIN/STDOUT and -V interface,
and Debian 03-Truncate's externally observable UNIX-address error.
"""
import gzip
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


def command(*arguments, **kwargs):
    return subprocess.check_output(arguments, text=True, stderr=subprocess.STDOUT, **kwargs)


def build_id(path, readelf):
    found = re.search(r"Build ID: ([0-9a-f]+)", command(str(readelf), "-n", str(path)))
    assert found, path
    return found.group(1)


def main():
    runtime, debug, metadata, source_marker, readelf, objcopy, *dependencies = map(Path, sys.argv[1:])
    source = source_marker.resolve().parent
    binaries = {"socat1", "filan", "procan"}
    scripts = {"socat-chain.sh", "socat-mux.sh", "socat-broker.sh"}
    # These paths are the original Make install and Debian helper contract.
    expected = {"usr/bin/" + name: 0o755 for name in binaries | scripts}
    expected.update({"usr/share/doc/socat/" + name: 0o644 for name in [
        "copyright", "README.Debian", "changelog.gz", "changelog.Debian.gz"]})
    expected.update({"usr/share/man/man1/socat1.1.gz": 0o644,
                     "usr/share/doc-base/socat": 0o644,
                     "usr/share/lintian/overrides/socat": 0o644})
    original_files = {}
    for pattern in (source / "debian/docs").read_text().splitlines():
        for path in source.glob(pattern):
            destination = "usr/share/doc/socat/" + path.name
            compressed = path.stat().st_size > 4096 and path.suffix not in (".html", ".css")
            if compressed:
                destination += ".gz"
            expected[destination] = 0o644
            original_files[destination] = path, compressed
    for name in (source / "debian/examples").read_text().splitlines():
        path = source / name
        destination = "usr/share/doc/socat/examples/" + name
        expected[destination] = 0o755 if path.stat().st_mode & 0o111 else 0o644
        original_files[destination] = path, False
    links = {"usr/bin/socat": "socat1", "usr/share/man/man1/socat.1.gz": "socat1.1.gz",
             "usr/share/man/man1/filan.1.gz": "socat.1.gz", "usr/share/man/man1/procan.1.gz": "socat.1.gz"}
    with tarfile.open(runtime) as archive:
        members = {member.name.removeprefix("./"): member for member in archive.getmembers() if not member.isdir()}
        assert set(members) == set(expected) | set(links), (sorted(set(members) - set(expected) - set(links)), sorted(set(expected) | set(links) - set(members)))
        for name, member in members.items():
            assert (member.uid, member.gid) == (0, 0), name
            if name in links:
                assert member.issym() and member.linkname == links[name], name
            else:
                assert member.isfile() and member.mode == expected[name], name
    info = json.loads(metadata.read_text())
    assert info["schema"] == 1 and info["module"] == "socat", info
    fields = info["packages"]["socat"]
    assert fields["control_fields"]["Version"] == "1.8.0.2-1", fields
    with tempfile.TemporaryDirectory(dir=os.environ["TEST_TMPDIR"]) as temporary:
        root = Path(temporary)
        for payload in [*dependencies, runtime]:
            with tarfile.open(payload) as archive:
                archive.extractall(root, filter="data")
        for destination, (original, compressed) in original_files.items():
            installed = root / destination
            content = gzip.decompress(installed.read_bytes()) if compressed else installed.read_bytes()
            assert content == original.read_bytes(), destination
        assert gzip.decompress((root / "usr/share/man/man1/socat1.1.gz").read_bytes()) == (source / "doc/socat.1").read_bytes()
        for installed, original in (("changelog.gz", "CHANGES"),
                                    ("changelog.Debian.gz", "debian/changelog")):
            assert gzip.decompress((root / "usr/share/doc/socat" / installed).read_bytes()) == (source / original).read_bytes()
        for name in scripts:
            assert (root / "usr/bin" / name).read_bytes() == (source / name).read_bytes(), name
        loaders = {p.resolve() for p in root.rglob("ld-linux-*.so.*") if p.is_file()}
        assert len(loaders) == 1, loaders
        libraries = sorted({str(p.parent) for p in root.rglob("*.so*") if p.is_file()})
        prefix = [str(loaders.pop()), "--inhibit-cache", "--library-path", os.pathsep.join(libraries)]
        environment = {k: v for k, v in os.environ.items() if not k.startswith("LD_")}
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
            dynamic = command(str(readelf), "-d", str(binary))
            assert not re.search(r"\((?:RPATH|RUNPATH)\)", dynamic), dynamic
            assert ".debug_info" not in command(str(readelf), "-SW", str(binary))
            assert not re.search(r"Line \d+ of", debugger(binary))
            identities[name] = build_id(binary, readelf)

        def installed_command(name, *args, **kwargs):
            return subprocess.check_output([*prefix, str(root / "usr/bin" / name), *args], env=environment, text=True, stderr=subprocess.STDOUT, timeout=20, **kwargs)
        # First startup check uses only -V before the behavioral assertions.
        version = installed_command("socat1", "-V")
        assert "socat version 1.8.0.2" in version, version
        for feature in ("WITH_OPENSSL", "WITH_READLINE", "WITH_LIBWRAP"):
            assert re.search(r"#define " + feature + r" 1\b", version), version
        for payload in ("short relay\n", "second input\n" * 257):
            assert installed_command("socat1", "-u", "STDIN", "STDOUT", input=payload) == payload
        result = subprocess.run([*prefix, str(root / "usr/bin/socat1"), "-u", "STDIN", "UNIX-CONNECT:" + str(root / ("x" * 200))], input="", env=environment, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=10)
        assert result.returncode == 1, (result.returncode, result.stdout)
        assert re.search(r"unix socket address \d+ characters long, max length is \d+", result.stdout), result.stdout
        for name in ("filan", "procan"):
            assert installed_command(name, "-h")
        process_metadata = installed_command("procan")
        namespace = re.search(r"^Network namespace: (.*)$", process_metadata, re.M)
        assert namespace and namespace[1] == os.readlink("/proc/self/ns/net"), process_metadata
        compiler = re.search(r"^// CC:\s+(.+)$", process_metadata, re.M)
        assert compiler and "/execroot/" not in compiler[1], process_metadata
        with tarfile.open(debug) as package:
            package.extractall(root, filter="data")
        for name, identity in identities.items():
            binary = root / "usr/bin" / name
            symbols = root / "usr/lib/debug/.build-id" / identity[:2] / (identity[2:] + ".debug")
            assert build_id(symbols, readelf) == identity
            assert ".debug_info" in command(str(readelf), "-SW", str(symbols))
            paths = command(str(readelf), "-p", ".debug_line_str", "-p", ".debug_str", str(symbols))
            assert "/execroot/" not in paths, paths
            section = root / (name + ".debuglink")
            command(str(objcopy), "--dump-section", f".gnu_debuglink={section}",
                    str(binary), str(root / (name + ".copy")))
            contents = section.read_bytes()
            assert contents.split(b"\0", 1)[0].decode() == symbols.name
            assert struct.unpack("<I", contents[-4:])[0] == zlib.crc32(symbols.read_bytes())
            location = debugger(binary)
            assert re.search(r'Line \d+ of .*' + re.escape(expected_sources[name]), location), location
        print(version)
        print("Installed Debian layout, runtime closure, feature parity, relay, UNIX-address and namespace behavior, and detached debug symbols passed")


if __name__ == "__main__":
    main()
