"""Check the source compiler and the installed shared runtime/debug pair."""

import argparse
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

from python.runfiles import runfiles


def output(*args, **kwargs):
    return subprocess.check_output(args, text=True, **kwargs)


def build_id(path):
    return re.findall(r"Build ID: ([0-9a-f]+)", output("readelf", "-n", str(path)))[0]


def main():
    parser = argparse.ArgumentParser()
    names = ["runtime", "debug", "consumer", "protoc", "metadata", "control", "changelog"]
    for name in names:
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    resolver = runfiles.Create()
    paths = {name: Path(resolver.Rlocation(getattr(args, name))).resolve() for name in names}
    metadata = json.loads(paths["metadata"].read_text())
    assert metadata["schema"] == 1 and metadata["module"] == "protobuf-legacy"
    assert set(metadata["packages"]) == {"libprotobuf32t64"}
    package = metadata["packages"]["libprotobuf32t64"]
    assert package["runtime_target"] == "//:libprotobuf_pkg"
    assert package["payload_sha256"] == hashlib.sha256(paths["runtime"].read_bytes()).hexdigest()
    for name in ["control", "changelog"]:
        assert metadata["_generated"][name + "_sha256"] == hashlib.sha256(paths[name].read_bytes()).hexdigest()
    fields = package["control_fields"]
    version = "3.21.12-11+deb13u1"
    assert fields["Package"] == "libprotobuf32t64" and fields["Version"] == version
    # The shared schema stores architecture once; verify it against the ELF below.
    assert metadata["architecture"] in ("amd64", "arm64")
    assert fields["Multi-Arch"] == "same"
    assert fields["Provides"] == "libprotobuf32 (= " + version + ")"
    assert fields["Replaces"] == "libprotobuf32"
    assert "libprotobuf32 (<< " + version + ")" in fields["Breaks"]
    for library in ["libc6", "libgcc-s1", "libstdc++6"]:
        assert re.search(r"(?:^|, )" + re.escape(library) + r"(?: \(|,|$)", fields["Depends"]), fields
    assert "${" not in json.dumps(fields)
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
        assert metadata["architecture"] == {62: "amd64", 183: "arm64"}[struct.unpack_from("<H", library.read_bytes(), 18)[0]]
        assert (root / "usr/share/doc/libprotobuf32t64/copyright").is_file()
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
        assert re.search(r'Line [0-9]+ of .*src/google/protobuf/message_lite\.cc', gdb), gdb
        print("Source protoc 3.21.12 and installed protobuf runtime/debug contract passed")


if __name__ == "__main__":
    main()
