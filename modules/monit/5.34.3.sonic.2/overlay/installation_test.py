"""Debian installation contract and device-free CLI/parser validation."""
import hashlib
import gzip
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
import zlib
from elf_metadata import Elf

PAYLOAD, SYMBOLS, CONTROL, METADATA, EXECUTABLE, CHANGES, CONTRIBUTORS, README = [Path(value).absolute() for value in sys.argv[1:]]
del sys.argv[1:]

class Installation(unittest.TestCase):
    def test_original_installation(self):
        package = json.loads(METADATA.read_text())["packages"]["monit"]
        self.assertEqual(package["control_fields"]["Version"], "1:5.34.3-1")
        self.assertEqual(package["control_fields"]["Architecture"], "amd64")
        self.assertEqual(package["payload_sha256"], hashlib.sha256(PAYLOAD.read_bytes()).hexdigest())
        with tarfile.open(PAYLOAD) as archive:
            files = {member.name.removeprefix("./"): member for member in archive}
            for path, mode in [("usr/bin/monit", 0o755), ("etc/monit/monitrc", 0o600), ("var/lib/monit/events", 0o700), ("etc/init.d/monit", 0o755), ("etc/pam.d/monit", 0o644)]:
                self.assertEqual((files[path].mode, files[path].uid, files[path].gid), (mode, 0, 0))
            elf = Elf(archive.extractfile(files["usr/bin/monit"]).read())
            self.assertEqual(elf.machine, 62)
            self.assertIsNone(elf.soname)
            dynamic = elf.by_name[".dynamic"]
            tags = [elf.unpack("qQ", off)[0] for off in range(dynamic[4], dynamic[4]+dynamic[5], dynamic[9])]
            self.assertFalse({15, 29} & set(tags), "deployment ELF must not retain build paths")
        with tarfile.open(CONTROL) as archive:
            files = {member.name: member for member in archive}
            self.assertEqual(files["postinst"].mode, 0o755)
            self.assertIn(b"monit.log", archive.extractfile(files["postinst"]).read())
            conffiles = set(archive.extractfile(files["conffiles"]).read().decode().splitlines())
            self.assertTrue({"/etc/monit/monitrc", "/etc/pam.d/monit", "/etc/init.d/monit", "/etc/logrotate.d/monit"} <= conffiles)

    def test_original_documentation(self):
        # Original dh_installchangelogs compat13 on the fixed original metadata
        # (before binding the new helper) trims43985 to10968 bytes and drops NEWS.
        with tarfile.open(PAYLOAD) as archive:
            files = {member.name.removeprefix("./"): member for member in archive}
            root = "usr/share/doc/monit/"
            changelog = gzip.decompress(archive.extractfile(files[root+"changelog.Debian.gz"]).read())
            self.assertEqual(hashlib.sha256(changelog).hexdigest(), "ff1a2d618d41b062b5e79ba6dbc4b48586cf7d04e3d44758b6279aa3c4d48387")
            self.assertEqual(gzip.decompress(archive.extractfile(files[root+"changelog.gz"]).read()), CHANGES.read_bytes())
            self.assertNotIn(root+"NEWS.Debian.gz", files)
            self.assertEqual(archive.extractfile(files[root+"CONTRIBUTORS"]).read(), CONTRIBUTORS.read_bytes())
            self.assertEqual(archive.extractfile(files[root+"README.Debian"]).read(), README.read_bytes())

    def test_version_and_original_sonic_repeat_grammar(self):
        env = {**os.environ, "LC_ALL":"C", "PATH":""}
        version = subprocess.run([str(EXECUTABLE), "--version"], env=env, capture_output=True, text=True, timeout=20)
        self.assertEqual(version.returncode, 0, version.stderr)
        self.assertIn("5.34.3", version.stdout)
        with tempfile.TemporaryDirectory() as temporary:
            config = Path(temporary)/"monitrc"
            config.write_text('set daemon 60\ncheck file example with path "'+str(config)+'"\n if does not exist then alert repeat every 2 cycles\n')
            config.chmod(0o600)
            result = subprocess.run([str(EXECUTABLE), "-t", "-c", str(config)], env=env, capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
            self.assertIn("Control file syntax OK", result.stdout+result.stderr)
            config.write_text('set daemon 60\ncheck file example with path "'+str(config)+'"\n if does not exist then alert repeat every banana cycles\n')
            invalid = subprocess.run([str(EXECUTABLE), "-t", "-c", str(config)], env=env, capture_output=True, text=True, timeout=20)
            self.assertNotEqual(invalid.returncode, 0, "the original parser must reject a nonnumeric repeat cycle count")

    def test_debug_pair(self):
        with tarfile.open(PAYLOAD) as payload, tarfile.open(SYMBOLS) as symbols:
            members = {member.name.removeprefix("./"):member for member in payload}
            elf = Elf(payload.extractfile(members["usr/bin/monit"]).read())
            name = "usr/lib/debug/.build-id/"+elf.build_id[:2]+"/"+elf.build_id[2:]+".debug"
            debug = {member.name.removeprefix("./"):member for member in symbols}
            contents = symbols.extractfile(debug[name]).read()
            dwarf = Elf(contents)
            self.assertEqual(dwarf.build_id, elf.build_id)
            self.assertTrue(".zdebug_info" in dwarf.by_name or dwarf.by_name.get(".debug_info", (0, 0, 0))[2] & 0x800, "original dh_strip compresses final DWARF")
            self.assertEqual(zlib.crc32(contents), elf.debuglink_crc)
            self.assertTrue(any(section in dwarf.by_name for section in (".debug_info", ".zdebug_info")))
            self.assertTrue(any(dwarf.by_name[section][5] > 0 for section in (".debug_info", ".zdebug_info") if section in dwarf.by_name), "original debug symbols contain usable DWARF")

if __name__ == "__main__":
    unittest.main()
