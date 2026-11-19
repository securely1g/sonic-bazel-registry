"""Check the Debian installation and matching-symbol artifact contracts.

The expected programs, paths and architecture conditions come from the original
SONiC Make/CMake install recipe. Target compilers and the installed driver are
inspected as files; this check executes only declared ELF inspection tools.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import struct
import subprocess
import tarfile
import tempfile
import zlib


def arguments():
    parser = argparse.ArgumentParser()
    for name in ("runtime", "debug", "metadata", "readelf", "objcopy", "control", "changelog"):
        parser.add_argument("--" + name, required=True, type=lambda value: Path(value).absolute())
    parser.add_argument("--arch", choices=("amd64", "arm64"), required=True)
    return parser.parse_args()


def run(*argv, env=None, cwd=None):
    try:
        return subprocess.check_output([str(arg) for arg in argv], text=True,
                                       stderr=subprocess.STDOUT, env=env, cwd=cwd)
    except subprocess.CalledProcessError as error:
        print(error.output, end="", flush=True)
        raise

def extract(archive, destination, unique=False):
    with tarfile.open(archive) as tar:
        names = [str(PurePosixPath(member.name)) for member in tar.getmembers()]
        if unique:
            assert len(names) == len(set(names)), "installation TAR repeats paths"
        tar.extractall(destination, filter="data")
        return tar.getmembers()

def build_id(readelf, path):
    notes = run(readelf, "-n", path)
    match = re.search(r"Build ID: ([0-9a-f]+)", notes)
    assert match, (path, notes)
    return match.group(1)

def check_symbols(args, binary, symbols_root, work):
    identifier = build_id(args.readelf, binary)
    symbols = symbols_root / "usr/lib/debug/.build-id" / identifier[:2] / (identifier[2:] + ".debug")
    assert build_id(args.readelf, symbols) == identifier
    link = work / (binary.name + ".debuglink")
    run(args.objcopy, "--dump-section=.gnu_debuglink=" + str(link), binary)
    data = link.read_bytes()
    assert data.split(b"\0", 1)[0].decode() == symbols.name
    endian = "<" if binary.read_bytes()[5] == 1 else ">"
    assert struct.unpack(endian + "I", data[-4:])[0] == zlib.crc32(symbols.read_bytes())
    assert ".debug_info" not in run(args.readelf, "-SW", binary), binary
    assert ".debug_info" in run(args.readelf, "-SW", symbols), symbols
    return identifier

def check_runtime(args, root, debug, work):
    programs = {"p4c-bm2-ss", "p4c-bm2-psa", "p4c-ebpf", "p4c-ubpf", "p4c-dpdk",
                "p4c-graphs", "p4c-pna-p4tc", "p4test"}
    if args.arch == "amd64":
        programs.add("p4testgen")
    assert {path.name for path in (root / "usr/bin").iterdir()} == programs | {"p4c"}
    machine = {"amd64": 62, "arm64": 183}[args.arch]
    identities = {}
    for name in sorted(programs):
        binary = root / "usr/bin" / name
        with binary.open("rb") as stream:
            header = stream.read(20)
        assert header[:5] == b"\x7fELF\x02", name
        endian = "<" if header[5] == 1 else ">"
        assert struct.unpack_from(endian + "H", header, 18)[0] == machine, name
        dynamic = run(args.readelf, "-d", binary)
        assert not re.search(r"\((?:RPATH|RUNPATH)\)", dynamic), (name, dynamic)
        needed = re.findall(r"\(NEEDED\).*?\[([^]]+)\]", dynamic)
        assert needed, name
        assert all(not library.startswith(("libprotobuf", "libprotoc")) for library in needed), needed
        identities[name] = check_symbols(args, binary, debug, work)
    return identities


def check_resources(root):
    include = root / "usr/share/p4c/p4include"
    for name in ("core.p4", "v1model.p4", "bmv2/psa.p4", "dpdk/psa.p4", "dpdk/pna.p4",
                 "tc/pna.p4", "pna.p4", "ebpf_model.p4", "ubpf_model.p4", "xdp_model.p4"):
        assert (include / name).is_file(), name
    driver = root / "usr/bin/p4c"
    assert re.match(rb"#!\s*/usr/bin/python3\s*\n", driver.read_bytes()), driver
    resources = root / "usr/share/p4c/p4c_src"
    assert {path.name for path in resources.glob("*.cfg")} == {
        "p4c.bmv2.cfg", "p4c.ebpf.cfg", "p4c.dpdk.cfg"}
    assert {path.name for path in resources.glob("*.py")} == {
        "__init__.py", "main.py", "driver.py", "config.py", "util.py"}


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def check_metadata(args, root):
    data = json.loads(args.metadata.read_text())
    assert data["schema"] == 1 and data["module"] == "p4c"
    assert data["architecture"] == args.arch
    assert set(data["packages"]) == {"p4lang-p4c"}
    package = data["packages"]["p4lang-p4c"]
    fields = package["control_fields"]
    assert fields["Package"] == "p4lang-p4c" and fields["Architecture"] == args.arch
    version = re.match(r"^\S+ \(([^)]+)\)", args.changelog.read_text()).group(1)
    assert fields["Version"] == version
    assert "${" not in fields.get("Depends", "")
    assert package["payload_sha256"] == digest(args.runtime)
    assert data["_generated"]["control_sha256"] == digest(args.control)
    assert data["_generated"]["changelog_sha256"] == digest(args.changelog)
    for path in package["required_paths"]:
        assert (root / path).is_file(), path
    return version


def main():
    args = arguments()
    with tempfile.TemporaryDirectory() as directory:
        work = Path(directory)
        root, debug = work / "runtime", work / "debug"
        for archive, destination in ((args.runtime, root), (args.debug, debug)):
            for member in extract(archive, destination, unique=True):
                assert (member.uid, member.gid) == (0, 0), member.name
                if member.isfile():
                    mode = 0o755 if archive == args.runtime and PurePosixPath(member.name).parent == PurePosixPath("usr/bin") else 0o644
                    assert member.mode == mode, (member.name, oct(member.mode))
        identities = check_runtime(args, root, debug, work)
        check_resources(root)
        version = check_metadata(args, root)
        print(json.dumps({"version": version, "architecture": args.arch,
                          "runtime_build_ids": identities, "target_programs_executed": False}))


if __name__ == "__main__":
    main()
