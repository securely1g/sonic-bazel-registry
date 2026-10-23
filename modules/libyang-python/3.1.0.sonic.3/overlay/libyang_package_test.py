"""Check the installed binding and the debug symbols shipped beside it."""

import os
from pathlib import Path
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


def command(*args):
    return subprocess.check_output(args, text=True, stderr=subprocess.STDOUT)


def build_id(path):
    match = re.search(r"Build ID: ([0-9a-f]+)", command("readelf", "-n", str(path)))
    assert match, f"Missing build ID: {path}"
    return match.group(1)


def main():
    runtime, debug, native, consumer, generated_metadata = map(
        lambda p: Path(p).resolve(), sys.argv[1:])
    with tempfile.TemporaryDirectory(dir=os.environ["TEST_TMPDIR"]) as temporary:
        root = Path(temporary)
        for archive in (runtime, native):
            with tarfile.open(archive) as package:
                package.extractall(root, filter="data")
        site = root / "usr/lib/python3/dist-packages"
        extension = site / "_libyang.so"
        metadata = site / "libyang-3.1.0.egg-info"
        expected_metadata = {path.name for path in generated_metadata.parent.iterdir()}
        assert {path.name for path in metadata.iterdir()} == expected_metadata
        for name in expected_metadata:
            installed = metadata / name
            assert installed.read_bytes() == (generated_metadata.parent / name).read_bytes(), name
            assert installed.stat().st_mode & 0o777 == 0o644, installed
        for source in sorted((consumer.parent / "libyang").iterdir()):
            if source.suffix == ".py" or source.name == "py.typed":
                installed = site / "libyang" / source.name
                assert installed.read_bytes() == source.read_bytes(), source
                assert installed.stat().st_mode & 0o777 == 0o644, installed
        assert (root / "usr/share/doc/python3-libyang/copyright").read_bytes() == (
            consumer.parent / "LICENSE"
        ).read_bytes()
        with tarfile.open(runtime) as package:
            assert package.getmember("usr/lib/python3/dist-packages/_libyang.so").mode == 0o555
            for name in expected_metadata:
                entry = package.getmember("usr/lib/python3/dist-packages/" + metadata.name + "/" + name)
                assert entry.uid == entry.gid == 0, entry
        assert ".debug_info" not in command("readelf", "-SW", str(extension))
        native_libraries = list((root / "usr/lib").rglob("libyang.so.3"))
        assert len(native_libraries) == 1, native_libraries
        library = native_libraries[0].resolve()

        # Only the installed binding may be imported. Its unchanged third-party
        # CFFI dependencies remain declared Bazel runfiles. Preloading this
        # libyang SONAME prevents a Bazel RPATH from selecting a build-tree copy.
        third_party = [Path(module.__file__).resolve() for module in (cffi, pycparser)]
        search = [site, *(path.parent.parent for path in third_party),
                  Path(_cffi_backend.__file__).resolve().parent]
        environment = dict(os.environ, PYTHONPATH=os.pathsep.join(map(str, search)),
                           LD_PRELOAD=str(library), LD_LIBRARY_PATH=str(library.parent))
        child = """
from importlib.metadata import distribution, distributions
import pathlib, re, runpy, sys
root = pathlib.Path(sys.argv[2])
site = root / 'usr/lib/python3/dist-packages'
installed = list(distributions(path=[str(site)]))
assert len(installed) == 1, installed
dist = distribution('libyang')
assert pathlib.Path(dist.locate_file('')).resolve() == site, dist
assert dist.metadata['Name'] == 'libyang' and dist.version == '3.1.0', dist.metadata
assert dist.metadata['Requires-Python'] == '>=3.6', dist.metadata
assert dist.metadata['License'] == 'MIT', dist.metadata
assert dist.read_text('top_level.txt').splitlines() == ['_libyang', 'libyang']
requirements = dist.requires
assert len(requirements) == 1 and re.fullmatch(
    r'''cffi\\s*;\\s*platform_python_implementation\\s*!=\\s*['"]PyPy['"]''',
    requirements[0]), requirements
checks = runpy.run_path(sys.argv[1])
for name in ('libyang', '_libyang'):
    path = pathlib.Path(checks[name].__file__).resolve()
    assert path.is_relative_to(root), (name, path)
loaded = {line.split()[-1] for line in pathlib.Path('/proc/self/maps').read_text().splitlines()
          if 'libyang.so.' in line}
assert loaded == {sys.argv[3]}, loaded
checks['check_consumer']()
"""
        subprocess.run([sys.executable, "-S", "-c", child, str(consumer), str(root), str(library)],
                       cwd=root, env=environment, check=True)

        def debugger():
            result = subprocess.run(["gdb", "-nx", "-batch", "-ex", "set debuginfod enabled off",
                           "-ex", f"set debug-file-directory {root}/usr/lib/debug",
                           "-ex", f"file {extension}", "-ex", "info line _cffi_f_ly_ctx_new"],
                                    text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            return result.stdout

        assert not re.search(r'Line \d+ of .*_libyang.c', debugger())
        with tarfile.open(debug) as package:
            package.extractall(root, filter="data")
        identity = build_id(extension)
        symbols = root / "usr/lib/debug/.build-id" / identity[:2] / (identity[2:] + ".debug")
        assert build_id(symbols) == identity
        assert ".debug_info" in command("readelf", "-SW", str(symbols))
        debuglink = root / "debuglink"
        command("objcopy", "--dump-section", f".gnu_debuglink={debuglink}",
                str(extension), str(root / "extension-copy"))
        link = debuglink.read_bytes()
        assert link.split(b"\0", 1)[0].decode() == symbols.name
        assert struct.unpack("<I", link[-4:])[0] == zlib.crc32(symbols.read_bytes())
        result = debugger()
        assert re.search(r'Line \d+ of .*_libyang.c', result), result
        print(result)
        print("Installed distribution metadata, binding, schema roundtrip, build ID, debuglink and GDB lookup passed")


if __name__ == "__main__":
    main()
