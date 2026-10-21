"""Exercise the deployed BMv2 programs, ABI, SDK and matching debug payload."""
import os
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


def build_id(path):
    match = re.search(r"Build ID: ([0-9a-f]+)", command("readelf", "-n", str(path)))
    assert match, path
    return match.group(1)


def main():
    runtime, debug, pi_runtime, consumer, config, grpc_config, copyright_file, *dependencies = [Path(x).resolve() for x in sys.argv[1:]]
    config_text = re.sub(r"/\*.*?\*/", "", config.read_text(), flags=re.S)
    for feature in ("THRIFT_ON", "NANOMSG_ON", "HAVE_PI_PI_H", "HAVE_PI_TARGET_PI_IMP_H", "HAVE_PI_P4INFO_H"):
        assert re.search(r"^#define " + feature + r"(?: 1)?\s*$", config_text, re.M), feature
    assert "--with-thrift" in grpc_config.read_text()
    programs = {"simple_switch", "simple_switch_grpc", "psa_switch", "pna_nic"}
    libraries = {"libbmall", "libbmp4apps", "libbmpi", "libbm_grpc_dataplane", "libruntimestubs", "libbmpdfixed", "libbmpdfixedthrift", "libsimpleswitch_runner", "libsimpleswitch_thrift", "libpnanic_thrift", "libpsaswitch_thrift"}
    with tempfile.TemporaryDirectory(dir=os.environ["TEST_TMPDIR"]) as temporary:
        root = Path(temporary)
        for archive in [*dependencies, pi_runtime, runtime]:
            with tarfile.open(archive) as package:
                package.extractall(root, filter="data")
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
            assert "Library soname: [" + name + ".so.0]" in command("readelf", "-d", str(files[0]))
            assert files[0].with_name(name + ".so.0").resolve() == files[0]
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
        identities = {}
        for binary in elfs:
            identities[binary] = build_id(binary)
            assert ".debug_info" not in command("readelf", "-SW", str(binary))
            dynamic = command("readelf", "-d", str(binary))
            assert not re.search(r"\((?:RPATH|RUNPATH)\)", dynamic), dynamic
            resolved = command(*prefix, "--list", str(binary), env=environment)
            assert "not found" not in resolved, resolved
            assert all(Path(path).resolve().is_relative_to(root) for path in re.findall(r"=> (/\S+)", resolved)), resolved
        for name in programs:
            output = command(*prefix, str(root / "usr/bin" / name), "--help", env=environment)
            assert "Usage" in output or "Options" in output or "options" in output, output
        assert "BMv2 installed SDK consumer passed" in command(*prefix, str(consumer), env=environment)

        def debug_line():
            return subprocess.run(["gdb", "-nx", "-batch", "-ex", "set debuginfod enabled off", "-ex", f"set debug-file-directory {root}/usr/lib/debug", "-ex", f"file {root}/usr/bin/simple_switch", "-ex", "info line main"], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30).stdout

        assert not re.search(r"Line \d+ of", debug_line())
        with tarfile.open(debug) as package:
            package.extractall(root, filter="data")
        for binary, identity in identities.items():
            symbols = root / "usr/lib/debug/.build-id" / identity[:2] / (identity[2:] + ".debug")
            assert build_id(symbols) == identity
            assert ".debug_info" in command("readelf", "-SW", str(symbols))
            section = root / "debug-link"
            command("objcopy", "--dump-section", f".gnu_debuglink={section}", str(binary), str(root / "elf-copy"))
            link = section.read_bytes()
            assert link.split(b"\0", 1)[0].decode() == symbols.name
            assert struct.unpack("<I", link[-4:])[0] == zlib.crc32(symbols.read_bytes())
        assert re.search(r"Line \d+ of .*main.cpp", debug_line())
        print("BMv2 native installed programs, 11 library ABIs, SDK, features and paired debug symbols passed")


if __name__ == "__main__":
    main()
