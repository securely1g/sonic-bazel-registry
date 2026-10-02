"""Check the source compiler and the installed shared runtime/debug pair."""

import argparse
import os
from pathlib import Path
import re
import struct
import subprocess
import tarfile
import tempfile
import zlib

from python.runfiles import runfiles


def output(*args, **kwargs):
    return subprocess.check_output(args, text=True, **kwargs)


def build_id(path):
    return re.findall(r"Build ID: ([0-9a-f]+)", output("readelf", "-n", str(path)))[0]


def main():
    parser = argparse.ArgumentParser()
    for name in ["runtime", "debug", "consumer", "protoc"]:
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    resolver = runfiles.Create()
    paths = {name: Path(resolver.Rlocation(getattr(args, name))).resolve() for name in ["runtime", "debug", "consumer", "protoc"]}
    assert output(str(paths["protoc"]), "--version").strip() == "libprotoc 3.21.12"
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        for name in ["runtime", "debug"]:
            with tarfile.open(paths[name]) as archive:
                members = archive.getmembers()
                assert members
                assert all(member.uid == member.gid == 0 for member in members)
                archive.extractall(root, filter="data")
        libraries = list(root.glob("usr/lib/*-linux-gnu/libprotobuf.so.32.0.12"))
        assert len(libraries) == 1, libraries
        library = libraries[0]
        soname = library.with_name("libprotobuf.so.32")
        assert soname.is_symlink() and os.readlink(soname) == library.name
        dynamic = output("readelf", "-d", str(library))
        assert "Library soname: [libprotobuf.so.32]" in dynamic
        assert "protobuf-lite" not in dynamic
        assert ".debug_info" not in output("readelf", "-S", str(library))
        identifier = build_id(library)
        debug = root / "usr/lib/debug/.build-id" / identifier[:2] / (identifier[2:] + ".debug")
        assert debug.is_file() and build_id(debug) == identifier
        assert ".debug_info" in output("readelf", "-S", str(debug))
        link = root / "debuglink"
        subprocess.run(["objcopy", "--dump-section", ".gnu_debuglink=" + str(link), str(library), str(root / "elf-copy")], check=True)
        data = link.read_bytes()
        assert data.split(b"\0", 1)[0].decode() == debug.name
        assert struct.unpack("<I", data[-4:])[0] == zlib.crc32(debug.read_bytes())
        environment = dict(os.environ)
        # A toolchain RPATH can precede LD_LIBRARY_PATH: preload the extracted
        # SONAME and verify dladdr resolves that exact source-built file.
        environment["LD_PRELOAD"] = str(library)
        environment["LD_LIBRARY_PATH"] = str(library.parent)
        result = output(str(paths["consumer"]), env=environment)
        assert result.strip() == "PROTOBUF_LIBRARY=" + str(library), result
        symbols = output("nm", "-D", "--defined-only", "-C", str(library))
        assert "google::protobuf::ShutdownProtobufLibrary()" in symbols
        assert "google::protobuf::DescriptorPool::generated_pool()" in symbols
        gdb = output("gdb", "-nx", "-batch", "-ex", "set debug-file-directory " + str(root / "usr/lib/debug"), "-ex", "file " + str(library), "-ex", "info line google::protobuf::ShutdownProtobufLibrary")
        assert re.search(r'Line [0-9]+ of .*common.cc', gdb), gdb
        print("Source protoc 3.21.12 and installed protobuf runtime/debug contract passed")


if __name__ == "__main__":
    main()
