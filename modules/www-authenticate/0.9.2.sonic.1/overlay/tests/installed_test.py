"""Consume the installed parser using its original distribution and README."""

import base64
import csv
from email.parser import BytesParser
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tarfile
import tempfile
import unittest


class InstalledParser(unittest.TestCase):
    def test_installed_distribution_and_documented_parser(self):
        original = BytesParser().parsebytes(Path(sys.argv[3]).read_bytes())
        prefix = PurePosixPath("usr/local/lib/python3.13/dist-packages")
        files = {}
        with tarfile.open(sys.argv[1], "r:") as archive:
            for entry in archive:
                path = PurePosixPath(entry.name)
                self.assertFalse(path.is_absolute())
                self.assertNotIn("..", path.parts)
                self.assertEqual((entry.uid, entry.gid), (0, 0))
                if entry.isdir():
                    self.assertEqual(entry.mode, 0o755)
                    continue
                self.assertTrue(entry.isfile())
                self.assertEqual(entry.mode, 0o644)
                name = str(path.relative_to(prefix))
                self.assertNotIn(name, files)
                files[name] = archive.extractfile(entry).read()
        self.assertEqual(files["www_authenticate.py"], Path(sys.argv[5]).read_bytes())
        metadata_names = [name for name in files if name.endswith(".dist-info/METADATA")]
        self.assertEqual(len(metadata_names), 1)
        distinfo = metadata_names[0].rsplit("/", 1)[0]
        required = {distinfo + "/" + name for name in ("METADATA", "WHEEL", "RECORD")}
        self.assertTrue(required <= set(files))
        self.assertTrue(set(files) <= required | {"www_authenticate.py", distinfo + "/INSTALLER"})
        metadata = BytesParser().parsebytes(files[metadata_names[0]])
        for field in ("Name", "Version", "Summary", "Author", "Author-email", "Home-page", "License"):
            self.assertEqual(metadata[field], original[field], field)
        self.assertEqual(metadata.get_payload(), Path(sys.argv[4]).read_text())
        self.assertEqual(metadata.get_all("Requires-Dist", []), [])
        runtime = json.loads(Path(sys.argv[2]).read_text())
        self.assertEqual(runtime["distribution"], original["Name"])
        self.assertEqual(runtime["version"], original["Version"])
        self.assertEqual(runtime["requires_dist"], [])
        self.assertEqual(runtime["entry_points"], {})
        record_name = distinfo + "/RECORD"
        rows = list(csv.reader(io.StringIO(files[record_name].decode())))
        self.assertEqual(len(rows), len(files))
        self.assertEqual({row[0] for row in rows}, set(files))
        for name, digest, size in rows:
            if name == record_name:
                self.assertEqual((digest, size), ("", ""))
            else:
                algorithm, _ = digest.split("=", 1)
                encoded = base64.urlsafe_b64encode(hashlib.new(algorithm, files[name]).digest()).rstrip(b"=").decode()
                self.assertEqual((digest, size), (algorithm + "=" + encoded, str(len(files[name]))))
        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory)
            for name, data in files.items():
                path = site / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            script = """
from collections import OrderedDict
import importlib.metadata, pathlib, sys
site = pathlib.Path(sys.argv[1])
sys.path.insert(0, str(site))
import www_authenticate
assert pathlib.Path(www_authenticate.__file__).is_relative_to(site)
basic = www_authenticate.parse('Basic realm="router, edge", charset=UTF-8')
assert isinstance(basic, OrderedDict)
assert basic['Basic'] == {'realm': 'router, edge', 'charset': 'UTF-8'}
assert www_authenticate.parse('Negotiate dG9rZW4=')['Negotiate'] == 'dG9rZW4='
multiple = www_authenticate.parse('Bearer, Basic realm="router"')
assert list(multiple.values()) == [None, {'realm': 'router'}]
assert 'Basic' in multiple and 'Bearer' in multiple
dist = importlib.metadata.distribution('www-authenticate')
assert pathlib.Path(dist.locate_file('')).is_relative_to(site)
assert dist.version == sys.argv[2]
"""
            result = subprocess.run([sys.executable, "-I", "-c", script, str(site), original["Version"]], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main(argv=[sys.argv[0]])
