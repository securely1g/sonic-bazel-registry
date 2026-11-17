"""Consume the direct TAR against original source and distribution metadata."""

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


class InstalledDistribution(unittest.TestCase):
    def test_installed_source_metadata_and_public_import(self):
        original = BytesParser().parsebytes(Path(sys.argv[3]).read_bytes())
        prefix = PurePosixPath("usr/local/lib/python3.13/dist-packages")
        payload = {}
        with tarfile.open(sys.argv[1], "r:") as archive:
            for member in archive:
                path = PurePosixPath(member.name)
                self.assertFalse(path.is_absolute())
                self.assertNotIn("..", path.parts)
                self.assertEqual((member.uid, member.gid), (0, 0))
                if member.isdir():
                    self.assertEqual(member.mode, 0o755)
                    continue
                self.assertTrue(member.isfile())
                self.assertEqual(member.mode, 0o644)
                name = str(path.relative_to(prefix))
                self.assertNotIn(name, payload)
                payload[name] = archive.extractfile(member).read()
        sources = {"blkinfo/" + Path(path).name: Path(path).read_bytes() for path in sys.argv[4:]}
        self.assertEqual({name: data for name, data in payload.items() if name.startswith("blkinfo/")}, sources)
        metadata_names = [name for name in payload if name.endswith(".dist-info/METADATA")]
        self.assertEqual(len(metadata_names), 1)
        distinfo = metadata_names[0].rsplit("/", 1)[0]
        required = {distinfo + "/" + name for name in ("METADATA", "WHEEL", "RECORD")}
        self.assertTrue(required <= set(payload))
        self.assertTrue(set(payload) <= set(sources) | required | {distinfo + "/INSTALLER"})
        metadata = BytesParser().parsebytes(payload[metadata_names[0]])
        for field in ("Name", "Version", "Summary", "Author", "Author-email", "Home-page", "License", "Keywords", "Description-Content-Type"):
            self.assertEqual(metadata[field], original[field], field)
        self.assertEqual(metadata.get_all("Classifier"), original.get_all("Classifier"))
        self.assertEqual(metadata.get_all("Requires-Dist", []), original.get_all("Requires-Dist", []))
        runtime = json.loads(Path(sys.argv[2]).read_text())
        self.assertEqual(runtime["distribution"], original["Name"])
        self.assertEqual(runtime["version"], original["Version"])
        self.assertEqual(runtime["requires_dist"], [])
        self.assertEqual(runtime["entry_points"], {})
        record_name = distinfo + "/RECORD"
        rows = list(csv.reader(io.StringIO(payload[record_name].decode())))
        self.assertEqual(len(rows), len(payload))
        self.assertEqual({row[0] for row in rows}, set(payload))
        for name, digest, size in rows:
            if name == record_name:
                self.assertEqual((digest, size), ("", ""))
            else:
                data = payload[name]
                algorithm, _ = digest.split("=", 1)
                encoded = base64.urlsafe_b64encode(hashlib.new(algorithm, data).digest()).rstrip(b"=").decode()
                self.assertEqual(digest, algorithm + "=" + encoded)
                self.assertEqual(size, str(len(data)))
        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory)
            for name, contents in payload.items():
                output = site / name
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(contents)
            # -I removes source/runfiles and PYTHONPATH. The missing executable
            # exercises the original public error using the real subprocess API.
            script = """
import importlib.metadata, json, pathlib, sys
site = pathlib.Path(sys.argv[1])
sys.path.insert(0, str(site))
import blkinfo
from blkinfo.errors import NoLsblkFound
assert pathlib.Path(blkinfo.__file__).is_relative_to(site)
assert blkinfo.BlkDiskInfo.__module__ == 'blkinfo.filters'
try:
    blkinfo.BlkDiskInfo()
except NoLsblkFound:
    pass
else:
    raise AssertionError('Missing lsblk must raise NoLsblkFound')
dist = importlib.metadata.distribution('blkinfo')
assert pathlib.Path(dist.locate_file('')).is_relative_to(site)
print(json.dumps({'name': dist.metadata['Name'], 'version': dist.version}))
"""
            result = subprocess.run([sys.executable, "-I", "-c", script, str(site)], env=dict(os.environ, PATH=""), capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(json.loads(result.stdout), {"name": original["Name"], "version": original["Version"]})


if __name__ == "__main__":
    unittest.main(argv=[sys.argv[0]])
