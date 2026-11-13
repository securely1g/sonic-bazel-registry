"""Distribution contract from upstream setup.py and Python wheel/RECORD specs."""
import base64
import configparser
import csv
import email
import hashlib
import io
from pathlib import Path
import sys
import tarfile
import unittest
import zipfile

WHEEL, INSTALL, LICENSE, README = map(Path, sys.argv[1:])
del sys.argv[1:]
DIST_INFO = "redis_dump_load-1.1.dist-info"
SITE = "usr/local/lib/python3.13/dist-packages/"
DOC = "share/doc/redis-dump-load/"


class DistributionContract(unittest.TestCase):
    def check_metadata(self, files, prefix):
        metadata = email.message_from_bytes(files[prefix + DIST_INFO + "/METADATA"])
        self.assertEqual(metadata["Name"].replace("_", "-"), "redis-dump-load")
        self.assertEqual(metadata["Version"], "1.1")
        self.assertEqual(metadata.get_all("Requires-Dist"), ["redis"])
        self.assertEqual(metadata["Summary"], "Dump and load redis databases")
        self.assertEqual(metadata["License"], "BSD")
        entries = configparser.ConfigParser()
        entries.read_string(files[prefix + DIST_INFO + "/entry_points.txt"].decode())
        self.assertEqual(dict(entries["console_scripts"]), {
            "redis-load": "redisdl:main", "redis-dump": "redisdl:main",
        })
        wheel = email.message_from_bytes(files[prefix + DIST_INFO + "/WHEEL"])
        self.assertEqual(wheel["Root-Is-Purelib"].lower(), "true")
        self.assertEqual(wheel["Tag"], "py3-none-any")

    def check_record(self, files, record_path, prefix=""):
        records = list(csv.reader(io.StringIO(files[record_path].decode())))
        seen = set()
        for name, digest, size in records:
            full = prefix + name
            # Installed RECORD paths may refer to scripts and data outside site-packages.
            full = str(Path(full))
            from posixpath import normpath
            full = normpath(full)
            self.assertNotIn(full, seen)
            seen.add(full)
            self.assertIn(full, files)
            if full == record_path:
                self.assertEqual((digest, size), ("", ""))
                continue
            content = files[full]
            self.assertEqual(int(size), len(content))
            algorithm, encoded = digest.split("=", 1)
            self.assertEqual(algorithm, "sha256")
            expected = base64.urlsafe_b64encode(hashlib.sha256(content).digest()).rstrip(b"=").decode()
            self.assertEqual(encoded, expected)
        self.assertEqual(seen, set(files))

    def test_wheel_and_install(self):
        with zipfile.ZipFile(WHEEL) as archive:
            wheel = {name: archive.read(name) for name in archive.namelist() if not name.endswith("/")}
        with tarfile.open(INSTALL) as archive:
            members = {member.name.removeprefix("./"): member for member in archive.getmembers() if member.isfile()}
            installed = {name: archive.extractfile(member).read() for name, member in members.items()}
        for files, prefix in [(wheel, ""), (installed, SITE)]:
            self.check_metadata(files, prefix)
            self.assertIn(prefix + "redisdl.py", files)
            compile(files[prefix + "redisdl.py"], "redisdl.py", "exec")
            self.check_record(files, prefix + DIST_INFO + "/RECORD", prefix)
        self.assertEqual(wheel["redisdl.py"], installed[SITE + "redisdl.py"])
        for name, original in [("LICENSE", LICENSE), ("README.rst", README)]:
            self.assertEqual(wheel["redis_dump_load-1.1.data/data/" + DOC + name], original.read_bytes())
            self.assertEqual(installed["usr/local/" + DOC + name], original.read_bytes())
        for name in ["redis-load", "redis-dump"]:
            path = "usr/local/bin/" + name
            self.assertEqual(installed[path].splitlines()[0], b"#!/usr/bin/python3")
            self.assertEqual(members[path].mode & 0o777, 0o755)
            self.assertEqual((members[path].uid, members[path].gid), (0, 0))


if __name__ == "__main__":
    unittest.main()
