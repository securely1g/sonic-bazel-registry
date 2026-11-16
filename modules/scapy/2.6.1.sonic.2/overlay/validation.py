"""Validate the exact installed wheel and upstream's native Linux test contract."""
import argparse
import email.parser
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

from installer import install
from installer.destinations import SchemeDictionaryDestination
from installer.sources import WheelFile
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet

VERSION = "2.6.1.dev0"


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def execute(argv, *, cwd, env, timeout=300):
    result = subprocess.run(argv, cwd=cwd, env=env, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, timeout=timeout)
    print(result.stdout, flush=True)
    require(result.returncode == 0, f"command failed ({result.returncode}): {argv}")
    return result.stdout


def isolated_environment(site=None):
    # Preserve declared third-party libraries, but never borrow Scapy from the
    # owner checkout/runfiles when validating an installed wheel.
    paths = [str(Path(p).resolve()) for p in sys.path if p and
             not (Path(p) / "scapy/__init__.py").is_file()]
    env = dict(os.environ)
    env.update(PYTHONPATH=os.pathsep.join(([str(site)] if site else []) + paths),
               PYTHONDONTWRITEBYTECODE="1", PYTHONNOUSERSITE="1", PIP_NO_INDEX="1",
               PYTHONHASHSEED="0", SOURCE_DATE_EPOCH="1730795594")
    env.pop("SCAPY_VERSION", None)
    return env


def install_wheel(wheel, root):
    site, scripts = root / "site", root / "bin"
    paths = {"purelib": str(site), "platlib": str(site), "scripts": str(scripts),
             "headers": str(root / "include"), "data": str(root)}
    destination = SchemeDictionaryDestination(paths, interpreter=sys.executable,
                                              script_kind="posix", bytecode_optimization_levels=())
    with WheelFile.open(wheel) as source:
        install(source, destination, additional_metadata={"INSTALLER": b"scapy-bazel-test\n"})
    return site, scripts


def archive_contract(wheel):
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
        info = next(n for n in names if n.endswith(".dist-info/METADATA"))
        metadata = email.parser.BytesParser().parsebytes(archive.read(info))
        payload = {n: {"sha256": hashlib.sha256(archive.read(n)).hexdigest(),
                       "mode": (archive.getinfo(n).external_attr >> 16) & 0o777}
                   for n in names if not n.endswith("/") and ".dist-info/" not in n}
        license_files = {n.rsplit("/", 1)[-1]: hashlib.sha256(archive.read(n)).hexdigest()
                         for n in names if ".dist-info/" in n and n.rsplit("/", 1)[-1] == "LICENSE"}
        entry = next(n for n in names if n.endswith(".dist-info/entry_points.txt"))
        entry_points = archive.read(entry).decode().strip()
        wheel_info = archive.read(next(n for n in names if n.endswith(".dist-info/WHEEL"))).decode()
        require("Tag: py3-none-any" in wheel_info and "Root-Is-Purelib: true" in wheel_info,
                "wheel is not the selected pure-Python distribution")
        return payload, metadata, license_files, entry_points


def reference_wheel(source, directory):
    private = directory / "source"
    private.mkdir()
    for name in ("scapy", "test", ".config"):
        shutil.copytree(source / name, private / name,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for name in ("setup.py", "pyproject.toml", "MANIFEST.in", "README.md", "LICENSE", "run_scapy"):
        shutil.copy2(source / name, private / name)
    (private / "doc").mkdir()
    shutil.copy2(source / "doc/scapy.1", private / "doc/scapy.1")
    env = isolated_environment()
    env["SCAPY_VERSION"] = VERSION
    execute([sys.executable, "setup.py", "bdist_wheel",
             "--dist-dir", str(directory / "reference")], cwd=private, env=env)
    result = directory / "reference" / f"scapy-{VERSION}-py3-none-any.whl"
    require(result.is_file(), "native Make-equivalent wheel filename/version changed")
    return result


INSTALLED_CHECK = r'''
from pathlib import Path
import importlib.metadata
import json
import sys
from unittest import mock
import scapy
from scapy.layers.inet import IP, UDP
from scapy.layers.inet6 import IPv6
from scapy.packet import Raw
from scapy.sendrecv import AsyncSniffer
root = Path(sys.argv[1]).resolve()
assert Path(scapy.__file__).resolve().is_relative_to(root)
assert scapy.VERSION == scapy.__version__ == importlib.metadata.version("scapy") == "2.6.1.dev0"
for packet in (IP(src="192.0.2.1", dst="192.0.2.2") / UDP(sport=42, dport=43) / Raw(b"SONiC"),
               IPv6(src="2001:db8::1", dst="2001:db8::2") / UDP(sport=42, dport=43) / Raw(b"SONiC")):
    decoded = packet.__class__(bytes(packet))
    assert decoded.src == packet.src and decoded.dst == packet.dst
    assert decoded[UDP].sport == 42 and decoded[UDP].dport == 43
    assert bytes(decoded[Raw]) == b"SONiC"
# Exercise the selected SONiC fix in the real AsyncSniffer control flow. No raw
# socket, physical interface, packet transmission or fabricated driver is used.
for interfaces in (["first", "missing", "last"], {"first": "one", "missing": "two", "last": "three"}):
    closed = []
    class Socket:
        nonblocking_socket = True
        def __init__(self, *, iface, **_kwargs):
            if iface == "missing":
                raise OSError("interface disappeared during creation")
            self.name = iface
        @staticmethod
        def select(_sockets, _timeout=None):
            return []
        def close(self):
            closed.append(self.name)
            if self.name == "first":
                raise OSError("close failed")
    AsyncSniffer()._run(iface=interfaces, L2socket=Socket, timeout=0.02)
    assert closed == ["first", "last"], closed
print(json.dumps({"status": "passed", "version": scapy.VERSION,
                  "installed_owner": True, "packet_roundtrips": ["IPv4", "IPv6"],
                  "async_sniffer_open_and_close_failures": ["list", "dict"]}))
'''


def wheel_test(wheel, source, root, receipts):
    reference = reference_wheel(source, root)
    actual, metadata, licenses, entries = archive_contract(wheel)
    expected, native_metadata, native_licenses, native_entries = archive_contract(reference)
    require(actual == expected, "wheel payload inventory/bytes/modes differ from native setuptools: " +
            repr({"missing": sorted(expected.keys() - actual.keys()),
                  "extra": sorted(actual.keys() - expected.keys()),
                  "changed": [p for p in actual.keys() & expected.keys() if actual[p] != expected[p]]}))
    require(licenses == native_licenses and licenses, "license payload differs")
    require(entries == native_entries, "console entry points differ")
    for field in ("Name", "Version", "Summary", "License", "Author", "Maintainer", "Keywords", "Description-Content-Type"):
        require(metadata[field] == native_metadata[field], "wheel metadata differs: " + field)
    require(metadata["Version"] == VERSION, "Make wheel version not preserved")
    require(SpecifierSet(metadata["Requires-Python"]) == SpecifierSet(native_metadata["Requires-Python"]),
            "Python requirement changed")
    for field in ("Provides-Extra", "Classifier", "Project-URL"):
        require(set(metadata.get_all(field, [])) == set(native_metadata.get_all(field, [])),
                "metadata differs: " + field)
    require({str(Requirement(x)) for x in metadata.get_all("Requires-Dist", [])} ==
            {str(Requirement(x)) for x in native_metadata.get_all("Requires-Dist", [])},
            "runtime dependency/extras contract changed")
    require(metadata.get_payload().strip() == native_metadata.get_payload().strip(), "description changed")
    site, scripts = install_wheel(wheel, root / "installed")
    env = isolated_environment(site)
    output = execute([sys.executable, "-c", INSTALLED_CHECK, str(site)], cwd=root, env=env)
    require((site / "scapy/py.typed").is_file(), "typing marker absent")
    require((root / "installed/share/man/man1/scapy.1").read_bytes() == (source / "doc/scapy.1").read_bytes(),
            "installed manpage changed")
    help_text = execute([str(scripts / "scapy"), "-h"], cwd=root, env=env)
    require("Usage" in help_text or "usage" in help_text, "installed CLI did not execute")
    shutil.copy2(reference, receipts / reference.name)
    differences = {field: {"native": native_metadata.get_all(field), "bazel": metadata.get_all(field)}
                   for field in set(native_metadata.keys()) | set(metadata.keys())
                   if native_metadata.get_all(field) != metadata.get_all(field)}
    (receipts / "wheel-validation.json").write_text(json.dumps({"status": "passed", "version": VERSION,
        "wheel_sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(), "payload": actual,
        "metadata_format_differences": differences, "installed_checks": output}, indent=2) + "\n")


def upstream_test(wheel, source, root, receipts):
    site, _ = install_wheel(wheel, root / "installed")
    for name in ("test", ".config"):
        shutil.copytree(source / name, site / name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for name in ("tls_nss_example.keys.txt", "tls_nss_example.pcap"):
        relative = Path("doc/notebooks/tls/raw_data") / name
        (site / relative).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / relative, site / relative)
    # Match the upstream package-maintainer simple mode, adding its independent
    # netaccess tag because this acceptance does not contact external hosts.
    excluded = ["netaccess", "libpcap", "samba", "tcpdump", "wireshark", "tshark", "ci_only", "vcan_socket",
                "automotive_comm", "scanner"]
    command = [sys.executable, "-m", "scapy.tools.UTscapy", "-c", "test/configs/linux.utsc", "-N", "-b",
               "-f", "xUnit", "-o", str(receipts / "upstream-xunit.xml")]
    for tag in excluded:
        command += ["-K", tag]
    env = isolated_environment(site)
    log = execute(command, cwd=site, env=env, timeout=1500)
    (receipts / "upstream.log").write_text(log)
    # Keep upstream's original concatenated xUnit campaign fragments verbatim.
    report = (receipts / "upstream-xunit.xml").read_text()
    test_count = report.count("<testcase ")
    require(test_count > 0 and "<error>" not in report, "upstream xUnit reports missing or failed tests")
    (receipts / "upstream-validation.json").write_text(json.dumps({"status": "passed",
        "version": VERSION, "wheel_sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
        "tests": test_count, "campaigns": report.count("<testsuite>"),
        "source_config": "test/configs/linux.utsc", "non_root": True,
        "excluded_upstream_tags": excluded, "owner_imports": "installed wheel only",
        "python": sys.version, "test_only_brotli": "1.2.0 (Python 3.13 wheel; original assertions unchanged)"}, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("wheel", "upstream"))
    parser.add_argument("wheel", type=Path)
    parser.add_argument("setup", type=Path)
    args = parser.parse_args()
    wheel, source = args.wheel.resolve(), args.setup.resolve().parent
    require(wheel.name == f"scapy-{VERSION}-py3-none-any.whl", "wheel filename changed")
    receipts = Path(os.environ.get("TEST_UNDECLARED_OUTPUTS_DIR", tempfile.mkdtemp(prefix="scapy-receipts-")))
    receipts.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="scapy-acceptance-") as temporary:
        (wheel_test if args.mode == "wheel" else upstream_test)(wheel, source, Path(temporary), receipts)


if __name__ == "__main__":
    main()
