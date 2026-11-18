"""Test the installed nnpy distribution, original socket tests and split symbols."""

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import struct
import subprocess
import sys
import tarfile
import tempfile
import zlib

import _cffi_backend
import cffi
import pycparser


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def extract(archive, destination, expected=None):
    with tarfile.open(archive) as package:
        names = set()
        files = set()
        for member in package:
            name = member.name.removeprefix("./").rstrip("/")
            if name in ("", "."):
                continue
            path = PurePosixPath(name)
            assert not path.is_absolute() and ".." not in path.parts and name not in names, name
            names.add(name)
            if expected is not None:
                assert member.uid == member.gid == 0, member
                assert member.mtime == 1672560000, (name, member.mtime)
                if member.isdir():
                    assert member.mode == 0o755 and any(p.startswith(name + "/") for p in expected), member
                else:
                    assert member.isfile() and name in expected, name
                    assert member.mode == expected[name], (name, member.mode)
                    files.add(name)
        if expected is not None:
            assert files == set(expected), (files, expected)
        package.extractall(destination, filter="data")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("runtime", "debug", "native", "source", "generation"):
        parser.add_argument("--" + name, type=lambda p: Path(p).resolve(), required=True)
    args = parser.parse_args()
    python_files = ["__init__.py", "errors.py", "socket.py", "tests.py", "constants.py"]
    metadata_files = ["PKG-INFO", "SOURCES.txt", "dependency_links.txt", "requires.txt", "top_level.txt"]
    prefix = "usr/lib/python3/dist-packages/"
    expected = {prefix + "nnpy/" + name: 0o644 for name in python_files}
    expected.update({prefix + "nnpy-1.4.2.egg-info/" + name: 0o644 for name in metadata_files})
    expected.update({prefix + "_nnpy.so": 0o755, "usr/share/doc/nnpy/LICENSE": 0o644})
    environment = {k: v for k, v in os.environ.items() if k not in ("LD_PRELOAD", "LD_LIBRARY_PATH", "LD_AUDIT", "PYTHONPATH")}
    environment.update(LC_ALL="C", DEBUGINFOD_URLS="", PYTHONDONTWRITEBYTECODE="1")
    with tempfile.TemporaryDirectory(prefix="nnpy-installed-", dir=os.environ.get("TEST_TMPDIR")) as temporary:
        root = Path(temporary)
        runtime, native, debug, empty = (root / name for name in ("runtime", "native", "debug", "empty"))
        for directory in (runtime, native, debug, empty):
            directory.mkdir()
        extract(args.runtime, runtime, expected)
        extract(args.native, native)
        extract(args.debug, debug)
        site = runtime / prefix
        extension = site / "_nnpy.so"
        library = (native / "usr/lib/x86_64-linux-gnu/libnanomsg.so.5").resolve()
        generation = json.loads(args.generation.read_text())
        assert generation["nanomsg_library_sha256"] == sha(library)
        assert generation["generated"]["constants.py"] == sha(site / "nnpy/constants.py")
        for name in python_files[:-1]:
            assert (site / "nnpy" / name).read_bytes() == (args.source.parent / "nnpy" / name).read_bytes(), name
        assert (runtime / "usr/share/doc/nnpy/LICENSE").read_bytes() == (args.source.parent / "LICENSE").read_bytes()
        for name, digest in generation["sources"].items():
            assert sha(args.source.parent / name) == digest, name

        # Python may import only the installed nnpy, plus declared external CFFI
        # dependencies. Preload the exact declared SONAME, and verify /proc/maps.
        third_party = [Path(m.__file__).resolve().parent.parent for m in (cffi, pycparser)]
        search = [site, *third_party, Path(_cffi_backend.__file__).resolve().parent]
        child_env = dict(environment, PYTHONPATH=os.pathsep.join(map(str, search)),
                         LD_PRELOAD=str(library), LD_LIBRARY_PATH=str(library.parent))
        child = r'''
from importlib.metadata import distribution
from pathlib import Path
import sys, unittest
import nnpy, _nnpy
from nnpy import tests
site, library = map(Path, sys.argv[1:])
assert Path(nnpy.__file__).resolve().is_relative_to(site)
assert Path(_nnpy.__file__).resolve() == site / '_nnpy.so'
dist = distribution('nnpy')
assert dist.version == '1.4.2' and dist.metadata['License'] == 'MIT'
assert Path(dist.locate_file('')).resolve() == site
assert dist.requires == ['cffi'], dist.requires
assert set(dist.read_text('top_level.txt').splitlines()) == {'nnpy', '_nnpy'}
loaded = {line.split()[-1] for line in Path('/proc/self/maps').read_text().splitlines() if 'libnanomsg.so.' in line}
assert loaded == {str(library)}, loaded
suite = unittest.defaultTestLoader.loadTestsFromTestCase(tests.Tests)
assert suite.countTestCases() == 2
result = unittest.TextTestRunner(verbosity=2).run(suite)
assert result.wasSuccessful() and result.testsRun == 2
'''
        subprocess.run([sys.executable, "-S", "-c", child, str(site), str(library)],
                       cwd=empty, env=child_env, check=True, timeout=30)
        hidden = site / "_nnpy.hidden"
        extension.rename(hidden)
        try:
            missing = subprocess.run([sys.executable, "-S", "-c", "import nnpy"], cwd=empty,
                                     env=child_env, capture_output=True, text=True, timeout=10)
            assert missing.returncode != 0 and "No module named '_nnpy'" in missing.stderr, missing.stderr
        finally:
            hidden.rename(extension)

        def elf(path, *options):
            return subprocess.check_output(["readelf", *options, path], text=True, env=environment)

        assert "Advanced Micro Devices X86-64" in elf(extension, "-h")
        dynamic = elf(extension, "-d")
        needed = set(re.findall(r"\(NEEDED\).*\[(.*?)\]", dynamic))
        assert "libnanomsg.so.5" in needed and not any("python" in n for n in needed), needed
        assert not re.search(r"\((?:RPATH|RUNPATH)\)", dynamic), dynamic
        identity = re.search(r"Build ID: ([0-9a-f]+)", elf(extension, "-n")).group(1)
        symbols = debug / "usr/lib/debug/.build-id" / identity[:2] / (identity[2:] + ".debug")
        assert re.search(r"Build ID: ([0-9a-f]+)", elf(symbols, "-n")).group(1) == identity
        assert ".debug_info" not in elf(extension, "-SW") and ".debug_info" in elf(symbols, "-SW")
        link_file = root / "debuglink"
        subprocess.run(["objcopy", "--dump-section", ".gnu_debuglink=" + str(link_file),
                        extension, root / "inspection-copy"], env=environment, check=True)
        link = link_file.read_bytes()
        assert link.split(b"\0", 1)[0].decode() == symbols.name
        assert struct.unpack("<I", link[-4:])[0] == zlib.crc32(symbols.read_bytes())
        for directory, expect_symbols in ((empty, False), (debug / "usr/lib/debug", True)):
            result = subprocess.run(["gdb", "--nx", "--nh", "--batch", "-iex", "set auto-load off",
                                     "-iex", "set debuginfod enabled off", "-ex", "set debug-file-directory " + str(directory),
                                     "-ex", "file " + str(extension), "-ex", "info line _cffi_f_nn_socket",
                                     "-ex", "ptype _cffi_f_nn_socket"],
                                    env=environment, capture_output=True, text=True, timeout=20)
            found = bool(re.search(r'Line \d+ of ".*_nnpy.c"', result.stdout))
            assert found == expect_symbols, result.stdout + result.stderr
            if expect_symbols:
                assert result.returncode == 0 and "type =" in result.stdout
        receipt = {"schema": 1, "runtime_sha256": sha(args.runtime), "debug_sha256": sha(args.debug),
                   "extension_sha256": sha(extension), "nanomsg_sha256": sha(library),
                   "build_id": identity, "upstream_tests": 2, "missing_extension_rejected": True,
                   "gdb_positive_and_negative": True, "distribution_metadata": "nnpy 1.4.2, MIT, cffi"}
        output = os.environ.get("TEST_UNDECLARED_OUTPUTS_DIR")
        if output:
            (Path(output) / "installed.json").write_text(json.dumps(receipt, indent=2) + "\n")
        print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
