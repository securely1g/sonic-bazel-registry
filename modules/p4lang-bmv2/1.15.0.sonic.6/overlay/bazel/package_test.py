"""Exercise the deployed BMv2 programs, ABI, SDK and matching debug payload."""
import copy
import os
import posixpath
from pathlib import Path
import re
import struct
import subprocess
import sys
import tarfile
import tempfile
import zlib


def command(*args, **kwargs):
    return subprocess.check_output(args, text=True, stderr=subprocess.STDOUT, timeout=30, **kwargs)


READELF = None
OBJCOPY = None
GDB = None


def build_id(path):
    match = re.search(r"Build ID: ([0-9a-f]+)", command(READELF, "-n", str(path)))
    assert match, path
    return match.group(1)


def private_root_filter(member, destination):
    # Debian links use container-absolute paths. Keep them inside the isolated
    # test root while retaining tarfile's path and special-file checks.
    if member.issym() and member.linkname.startswith("/"):
        member = copy.copy(member)
        member.linkname = posixpath.relpath(
            member.linkname.lstrip("/") or ".", posixpath.dirname(member.name) or ".",
        )
    return tarfile.data_filter(member, destination)


def main():
    global READELF, OBJCOPY, GDB
    runtime, debug, pi_runtime, development, consumer, copyright_file = [Path(x).resolve() for x in sys.argv[1:7]]
    # Preserve executable runfile paths; resolving launcher symlinks loses their
    # sibling runfiles trees and declared execution-side runtime.
    READELF, OBJCOPY, GDB = [str(Path(x).absolute()) for x in sys.argv[7:10]]
    dependencies = [Path(x).resolve() for x in sys.argv[10:]]
    programs = {"simple_switch", "simple_switch_grpc", "psa_switch", "pna_nic"}
    libraries = {"libbmall", "libbmp4apps", "libbmpi", "libbm_grpc_dataplane", "libruntimestubs", "libbmpdfixed", "libbmpdfixedthrift", "libsimpleswitch_runner", "libsimpleswitch_thrift", "libpnanic_thrift", "libpsaswitch_thrift"}
    with tempfile.TemporaryDirectory(dir=os.environ["TEST_TMPDIR"]) as temporary:
        root = Path(temporary)
        for archive in dependencies:
            with tarfile.open(archive) as package:
                package.extractall(root, filter=private_root_filter)
        for archive in (pi_runtime, runtime, development):
            with tarfile.open(archive) as package:
                package.extractall(root, filter="data")
        # Public headers and static archives are installed by upstream Automake.
        assert (root / "usr/include/bm/bm_sim/bytecontainer.h").is_file()
        assert list(root.glob("usr/lib/*-linux-gnu/libbmall.a"))
        elfs = []
        with tarfile.open(runtime) as package:
            for member in package.getmembers():
                assert (member.uid, member.gid) == (0, 0), member.name
                if member.isfile() and package.extractfile(member).read(4) == b"\x7fELF":
                    elfs.append(root / member.name)
        assert {p.name for p in elfs} == programs | {n + ".so.0.0.0" for n in libraries}
        for name in libraries:
            files = list(root.glob("usr/lib/*-linux-gnu/" + name + ".so.0.0.0"))
            assert len(files) == 1, files
            assert "Library soname: [" + name + ".so.0]" in command(READELF, "-d", str(files[0]))
            assert files[0].with_name(name + ".so.0").resolve() == files[0]
            assert files[0].with_name(name + ".so").resolve() == files[0]
            assert files[0].with_name(name + ".a").is_file(), name
            assert files[0].with_name(name + ".la").is_file(), name
        assert (root / "usr/share/doc/p4lang-bmv2/copyright").read_bytes() == copyright_file.read_bytes()
        for relative in ("bm_runtime/standard/Standard.py", "sswitch_runtime/SimpleSwitch.py", "p4/bm/dataplane_interface_pb2.py", "bm/pdfixed/mc_pd_rpc/mc.py"):
            assert (root / "usr/lib/python3/dist-packages" / relative).is_file(), relative
        for name in ("bm_CLI", "bm_p4dbg", "bm_nanomsg_events", "simple_switch_CLI", "psa_switch_CLI", "pna_nic_CLI"):
            assert os.access(root / "usr/bin" / name, os.X_OK), name

        loaders = {p.resolve() for p in root.rglob("ld-linux-*.so.*") if p.is_file()}
        assert len(loaders) == 1, loaders
        search = sorted({str(p.parent) for p in root.rglob("*.so*") if p.is_file()})
        prefix = [str(loaders.pop()), "--inhibit-cache", "--library-path", os.pathsep.join(search)]
        environment = dict(os.environ)
        for variable in ("LD_PRELOAD", "LD_LIBRARY_PATH", "LD_AUDIT"):
            environment.pop(variable, None)
        # Avoid host dynamic-loader variables even for the declared inspection
        # tools; execution runtimes resolve their own pinned files.
        for variable in ("LD_PRELOAD", "LD_LIBRARY_PATH", "LD_AUDIT"):
            os.environ.pop(variable, None)
        identities = {}
        for binary in elfs:
            identities[binary] = build_id(binary)
            assert ".debug_info" not in command(READELF, "-SW", str(binary))
            dynamic = command(READELF, "-d", str(binary))
            assert not re.search(r"\((?:RPATH|RUNPATH)\)", dynamic), dynamic
            resolved = command(*prefix, "--list", str(binary), env=environment)
            assert "not found" not in resolved, resolved
            assert all(Path(path).resolve().is_relative_to(root) for path in re.findall(r"=> (/\S+)", resolved)), resolved
        for name in programs:
            output = command(*prefix, str(root / "usr/bin" / name), "--help", env=environment)
            assert "Usage" in output or "Options" in output or "options" in output, output
            # The fixed orig archive retains .git/HEAD at 68f4a978;
            # tools/get_version.sh appends its first eight characters.
            assert command(*prefix, str(root / "usr/bin" / name), "--version", env=environment).strip() == "1.15.0-68f4a978"
        assert "BMv2 installed SDK consumer passed" in command(*prefix, str(consumer), env=environment)

        def debug_line():
            return subprocess.run([GDB, "-nx", "-batch", "-ex", "set debuginfod enabled off", "-ex", f"set debug-file-directory {root}/usr/lib/debug", "-ex", f"file {root}/usr/bin/simple_switch", "-ex", "info line main"], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30).stdout

        assert not re.search(r"Line \d+ of", debug_line())
        with tarfile.open(debug) as package:
            package.extractall(root, filter="data")
        for binary, identity in identities.items():
            symbols = root / "usr/lib/debug/.build-id" / identity[:2] / (identity[2:] + ".debug")
            assert build_id(symbols) == identity
            assert ".debug_info" in command(READELF, "-SW", str(symbols))
            section = root / "debug-link"
            command(OBJCOPY, "--dump-section", f".gnu_debuglink={section}", str(binary), str(root / "elf-copy"))
            link = section.read_bytes()
            assert link.split(b"\0", 1)[0].decode() == symbols.name
            assert struct.unpack("<I", link[-4:])[0] == zlib.crc32(symbols.read_bytes())
        assert re.search(r"Line \d+ of .*main.cpp", debug_line())
        # Generated service modules must preserve the upstream Thrift wire API.
        # This reaches installed Python files and the declared APT runtime.
        python_environment = dict(environment, PYTHONPATH=str(root / "usr/lib/python3/dist-packages"), PYTHONNOUSERSITE="1", PYTHONHOME=str(root / "usr"))
        command(*prefix, str(root / "usr/bin/python3"), "-s", "-c", """
from thrift.protocol import TBinaryProtocol
from thrift.transport import TTransport
from bm_runtime.standard.ttypes import BmCounterValue
from sswitch_runtime import SimpleSwitch
value = BmCounterValue(bytes=257, packets=3)
transport = TTransport.TMemoryBuffer()
value.write(TBinaryProtocol.TBinaryProtocol(transport))
restored = BmCounterValue()
restored.read(TBinaryProtocol.TBinaryProtocol(TTransport.TMemoryBuffer(transport.getvalue())))
assert restored.bytes == 257 and restored.packets == 3
assert hasattr(SimpleSwitch.Client, 'set_egress_queue_depth')
""", env=python_environment)
        print("BMv2 native installed programs, 11 library ABIs, SDK, features and paired debug symbols passed")


if __name__ == "__main__":
    main()
