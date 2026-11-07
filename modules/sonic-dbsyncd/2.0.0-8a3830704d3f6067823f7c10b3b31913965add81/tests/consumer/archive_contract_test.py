"""Verify a fetched owner's wheel, installed TAR and source-free imports."""

import base64
import csv
from email.parser import BytesParser
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tarfile
import tempfile
import unittest
import zipfile

WHEEL, TAR, SETUP = map(Path, sys.argv[1:4])
sys.argv = sys.argv[:1]
PREFIX = "usr/local/lib/python3.13/dist-packages/"


class ArchiveContractTest(unittest.TestCase):
    def test_owner_wheel_and_installed_payload(self):
        root = SETUP.resolve().parent
        expected = {str(path.relative_to(root / "src")): path.read_bytes()
                    for package in ("lldp_syncd", "sonic_syncd")
                    for path in (root / "src" / package).glob("*.py")}
        self.assertEqual(len(expected), 7)
        with zipfile.ZipFile(WHEEL) as wheel, tarfile.open(TAR) as layer:
            self.assertEqual({name for name in wheel.namelist() if name.endswith(".py")}, set(expected))
            for name, contents in expected.items():
                self.assertEqual(wheel.read(name), contents, name)
            names = wheel.namelist()
            metadata_name, = [name for name in names if name.endswith(".dist-info/METADATA")]
            metadata = BytesParser().parsebytes(wheel.read(metadata_name))
            self.assertEqual(metadata["Name"], "sonic-d")
            self.assertEqual(metadata["Version"], "2.0.0")
            self.assertEqual(metadata["License"], "Apache 2.0")
            license_name, = [name for name in names if name.endswith("/licenses/LICENSE")]
            self.assertEqual(wheel.read(license_name), (root / "LICENSE").read_bytes())
            record_name, = [name for name in names if name.endswith(".dist-info/RECORD")]
            for name, digest, size in csv.reader(io.StringIO(wheel.read(record_name).decode())):
                if name == record_name:
                    continue
                contents = wheel.read(name)
                self.assertEqual(int(size), len(contents), name)
                self.assertEqual(digest, "sha256=" + base64.urlsafe_b64encode(
                    hashlib.sha256(contents).digest()).rstrip(b"=").decode(), name)
            members = layer.getmembers()
            regular = {}
            for member in members:
                path = PurePosixPath(member.name)
                self.assertFalse(path.is_absolute() or ".." in path.parts, member.name)
                self.assertTrue(member.isfile() or member.isdir(), member.name)
                self.assertEqual((member.uid, member.gid, member.mtime), (0, 0, 0), member.name)
                self.assertEqual(member.mode, 0o644 if member.isfile() else 0o755, member.name)
                if member.isfile():
                    regular[str(path)] = layer.extractfile(member).read()
            self.assertEqual({name for name in regular if name.endswith(".py")},
                             {PREFIX + name for name in expected})
            for name in names:
                if not name.endswith("/") and name != record_name:
                    self.assertEqual(regular[PREFIX + name], wheel.read(name), name)

    def test_imports_from_installed_tar_without_source(self):
        with tempfile.TemporaryDirectory() as directory, tarfile.open(TAR) as layer:
            root = Path(directory)
            layer.extractall(root, filter="data")
            site = root / PREFIX
            probe = """
import importlib, importlib.metadata, pathlib, sys
site = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(site))
for name in ('sonic_syncd', 'sonic_syncd.interface'):
    module = importlib.import_module(name)
    assert pathlib.Path(module.__file__).resolve().is_relative_to(site), module.__file__
assert importlib.metadata.version('sonic-d') == '2.0.0'
from sonic_syncd import SonicSyncDaemon
assert SonicSyncDaemon(update_frequency=5)._update_frequency == 5
"""
            result = subprocess.run([sys.executable, "-I", "-c", probe, str(site)],
                                    cwd=root, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    result = unittest.main(exit=False).result
    output = os.environ.get("TEST_UNDECLARED_OUTPUTS_DIR")
    if output:
        Path(output, "archive-contract.json").write_text(json.dumps({
            "status": "passed" if result.wasSuccessful() else "failed",
            "wheel_sha256": hashlib.sha256(WHEEL.read_bytes()).hexdigest(),
            "runtime_tar_sha256": hashlib.sha256(TAR.read_bytes()).hexdigest(),
            "tests": result.testsRun,
            "scope": "Owner payload and installed stdlib-only imports; native library import tested separately",
        }, indent=2) + "\n")
    raise SystemExit(not result.wasSuccessful())
