"""Original Make installation and the CLI's device-free help contract."""
import hashlib
import json
from elf_metadata import Elf
import pathlib
import subprocess
import sys
import tarfile
import unittest

PAYLOAD, CONTROL, EXECUTABLE, ORIGINAL, METADATA = sys.argv[1:]
sys.argv[1:] = []

class Installation(unittest.TestCase):
    def test_original_installation(self):
        with tarfile.open(PAYLOAD) as archive:
            files = [member for member in archive if member.isfile()]
            self.assertEqual([member.name for member in files], ["usr/local/bin/sedutil-cli"])
            member = files[0]
            self.assertEqual((member.mode, member.uid, member.gid), (0o755, 0, 0))
            self.assertEqual(archive.extractfile(member).read(), pathlib.Path(ORIGINAL).read_bytes())
        with tarfile.open(CONTROL) as archive:
            fields = dict(line.split(": ", 1) for line in archive.extractfile("control").read().decode().splitlines())
        self.assertEqual(fields, {"Package": "sedutil", "Version": "1.15-5ad84d8", "Architecture": "amd64", "Maintainer": "SONiC Team", "Description": "SED management utility"})

    def test_runtime_metadata(self):
        metadata = json.loads(pathlib.Path(METADATA).read_text())
        self.assertEqual(metadata["architecture"], "amd64")
        self.assertEqual(set(metadata["packages"]), {"sedutil"})
        package = metadata["packages"]["sedutil"]
        self.assertEqual(package["runtime_target"], "//:sedutil.runtime")
        self.assertEqual(package["payload_sha256"], hashlib.sha256(pathlib.Path(PAYLOAD).read_bytes()).hexdigest())
        with tarfile.open(CONTROL) as archive:
            original = dict(line.split(": ", 1) for line in archive.extractfile("control").read().decode().splitlines())
        for key, value in original.items():
            self.assertEqual(package["control_fields"][key], value, key)
        self.assertNotIn("Depends", package["control_fields"])
        self.assertFalse(package["shlibdeps"])
        self.assertEqual(package["elf_needed"], {"usr/local/bin/sedutil-cli": Elf(pathlib.Path(ORIGINAL).read_bytes()).needed})
        self.assertEqual(package["required_paths"], ["usr/local/bin/sedutil-cli"])

    def test_safe_help(self):
        result = subprocess.run([EXECUTABLE, "--help"], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0x88, result.stderr)  # DTAERROR_COMMAND_ERROR: --help returns before device construction.
        self.assertIn("sedutil", result.stdout.lower())
        self.assertIn("--scan", result.stdout)

if __name__ == "__main__":
    unittest.main()
