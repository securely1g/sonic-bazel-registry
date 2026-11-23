"""Verify native py_wheel's public metadata, license layout and permissions."""
import base64
import csv
from email.parser import BytesParser
import hashlib
import io
import stat
import sys
import unittest
import zipfile

WHEELS = sys.argv[1:]
del sys.argv[1:]

class MetadataContract(unittest.TestCase):
    def test_archive_contract(self):
        expectations = [
            (WHEELS[0], 0o777, "2.1", None, None, None, []),
            (WHEELS[1], 0o644, "2.4", "Ada Maintainer, Grace Maintainer", "Ada <ada@example.org>, grace@example.org", "network, packets", ["LICENSE", "notices/NOTICE"]),
            (WHEELS[2], 0o755, "2.1", "Changed Maintainer", None, "alternative", []),
        ]
        for path, mode, version, maintainer, email, keywords, licenses in expectations:
            with self.subTest(wheel=path), zipfile.ZipFile(path) as whl:
                names = whl.namelist()
                info = next(n.rsplit("/", 1)[0] for n in names if n.endswith(".dist-info/METADATA"))
                metadata = BytesParser().parsebytes(whl.read(info + "/METADATA"))
                self.assertEqual(metadata["Metadata-Version"], version)
                self.assertEqual(metadata["Maintainer"], maintainer)
                self.assertEqual(metadata["Maintainer-email"], email)
                self.assertEqual(metadata["Keywords"], keywords)
                self.assertEqual(metadata.get_all("License-File", []), licenses)
                for member in whl.infolist():
                    self.assertTrue(stat.S_ISREG(member.external_attr >> 16), member.filename)
                    self.assertEqual(stat.S_IMODE(member.external_attr >> 16), mode, member.filename)
                for relative in licenses:
                    self.assertIn(info + "/licenses/" + relative, names)
                if licenses:
                    self.assertEqual(whl.read(info + "/licenses/LICENSE"), b"Example license text\n")
                    self.assertEqual(whl.read(info + "/licenses/notices/NOTICE"), b"Example nested notice\n")
                    self.assertIn("fixture = fixture:main", whl.read(info + "/entry_points.txt").decode())
                records = list(csv.reader(io.StringIO(whl.read(info + "/RECORD").decode())))
                self.assertEqual({row[0] for row in records}, set(names))
                for filename, digest, size in records:
                    if filename == info + "/RECORD":
                        self.assertEqual((digest, size), ("", ""))
                        continue
                    data = whl.read(filename)
                    self.assertEqual(int(size), len(data))
                    expected = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode()
                    self.assertEqual(digest, "sha256=" + expected)

if __name__ == "__main__":
    unittest.main()
