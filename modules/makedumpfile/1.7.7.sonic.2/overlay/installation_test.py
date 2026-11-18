"""Exercise the original installed package contract with declared APT tools."""
import argparse
import email
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tarfile
import tempfile
import unittest
import zlib
from elf_metadata import Elf

PARSER = argparse.ArgumentParser()
for _name in ["runtime", "archive", "metadata", "control", "symbols", "build-binary", "source", "debian", "pigz", "perl", "readelf"]:
    PARSER.add_argument("--" + _name, type=Path, required=True)
ARGS = PARSER.parse_args()
EXPECTED_FILES = {
    "usr/bin/makedumpfile": 0o755,
    "usr/bin/makedumpfile-R.pl": 0o755,
    "usr/share/makedumpfile/makedumpfile.conf.sample": 0o644,
    "usr/share/man/man8/makedumpfile.8.gz": 0o644,
    "usr/share/man/man5/makedumpfile.conf.5.gz": 0o644,
    "usr/share/doc/makedumpfile/copyright": 0o644,
    "usr/share/doc/makedumpfile/changelog.Debian.gz": 0o644,
}


def run(command, data=None):
    env = {k: v for k, v in os.environ.items() if not k.startswith("LD_")}
    env.update(PATH="", LANG="C", LC_ALL="C")
    return subprocess.run(list(map(str, command)), input=data, env=env, check=True, capture_output=True).stdout


class InstalledPackage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = ARGS.runtime.absolute()
        cls.program = cls.runtime / "usr/bin/makedumpfile"
        cls.launcher = cls.runtime / "bin/makedumpfile"
        cls.version = run([cls.launcher, "-v"]).decode()
        cls.help = run([cls.launcher, "-h"]).decode()
        cls.files = {}
        with tarfile.open(ARGS.archive) as archive:
            cls.members = archive.getmembers()
            for member in cls.members:
                if member.isfile():
                    cls.files[member.name.removeprefix("./")] = archive.extractfile(member).read()
        cls.elf = Elf(cls.files["usr/bin/makedumpfile"])
        cls.source = ARGS.source.absolute().parent
        cls.debian = ARGS.debian.absolute().parent

    def test_installed_layout(self):
        self.assertEqual(set(self.files), set(EXPECTED_FILES))
        for member in self.members:
            self.assertEqual((member.uid, member.gid), (0, 0))
            # sonic_deploy_tar's public fallback is 1672560000; the six
            # original resource entries explicitly override it with time=0.
            expected_time = 1672560000 if member.name.removeprefix("./") == "usr/bin/makedumpfile" else 0
            self.assertEqual(member.mtime, expected_time)
            if member.isfile():
                self.assertEqual(member.mode, EXPECTED_FILES[member.name.removeprefix("./")])
        self.assertEqual(self.files["usr/bin/makedumpfile"], self.program.read_bytes())
        for path, source in {
            "usr/bin/makedumpfile-R.pl": self.source / "makedumpfile-R.pl",
            "usr/share/makedumpfile/makedumpfile.conf.sample": self.source / "makedumpfile.conf",
            "usr/share/doc/makedumpfile/copyright": self.debian / "copyright",
        }.items():
            self.assertEqual(self.files[path], source.read_bytes())
        makefile = (self.source / "Makefile").read_text()
        version = re.search(r"^VERSION=(.+)$", makefile, re.M).group(1)
        date = re.search(r"^DATE=(.+)$", makefile, re.M).group(1)
        for path, template in [
            ("usr/share/man/man8/makedumpfile.8.gz", "makedumpfile.8.in"),
            ("usr/share/man/man5/makedumpfile.conf.5.gz", "makedumpfile.conf.5.in"),
        ]:
            expected = (self.source / template).read_text().replace("@VERSION@", version).replace("@DATE@", date).encode()
            self.assertEqual(run([ARGS.pigz, "-dc"], self.files[path]), expected)
        # Independently recorded original Trixie dh_installchangelogs output
        # for the fixed1:1.7.7-1 source:6627 bytes, not its56285-byte raw input.
        changelog = run([ARGS.pigz, "-dc"], self.files["usr/share/doc/makedumpfile/changelog.Debian.gz"])
        self.assertEqual(hashlib.sha256(changelog).hexdigest(), "b6d0a2d1454c877aaa2f58be323355650773db0a37b279230455c32e9d618395")
        run([ARGS.perl, "-c", self.runtime / "usr/bin/makedumpfile-R.pl"])

    def test_original_version_and_compression(self):
        self.assertIn("version 1.7.7 (released on 21 Apr 2025)", self.version)
        self.assertIn("LZO support:\n  enabled", self.help)
        self.assertIn("zstd support:\n  enabled", self.help)
        self.assertIn("liblzo2.so.2", self.elf.needed)
        self.assertIn("libzstd.so.1", self.elf.needed)
        self.assertRegex(self.version, r"snappy\s+disabled")
        manifest = json.loads((self.runtime / "toolchain.json").read_text())
        loader = self.runtime / manifest["loader"]
        libraries = os.pathsep.join(str(self.runtime / p) for p in manifest["library_directories"])
        listing = run([loader, "--inhibit-cache", "--library-path", libraries, "--list", self.program]).decode()
        allowed = {p.resolve() for p in self.runtime.rglob("*") if p.is_file() and ".so" in p.name}
        for path in re.findall(r"=>\s+(/\S+)", listing):
            self.assertIn(Path(path).resolve(), allowed, path)

    def test_original_metadata_and_control(self):
        receipt = json.loads(ARGS.metadata.read_text())
        self.assertEqual(receipt["schema"], 1)
        self.assertEqual(receipt["module"], "makedumpfile")
        package = receipt["packages"]["makedumpfile"]
        fields = package["control_fields"]
        self.assertEqual(fields["Package"], "makedumpfile")
        version = re.search(r"^makedumpfile \(([^)]+)\)", (self.debian / "changelog").read_text()).group(1)
        self.assertEqual(fields["Version"], version)
        self.assertEqual(fields["Architecture"], "amd64")
        paragraphs = (self.debian / "control").read_text().split("\n\n")
        source = email.message_from_string(paragraphs[0])
        original = email.message_from_string(next(p for p in paragraphs if p.startswith("Package: makedumpfile\n")))
        for name in ["Maintainer", "Section", "Priority", "Homepage"]:
            self.assertEqual(fields[name], original.get(name, source.get(name)))
        for name in ["Description", "Recommends", "Replaces"]:
            self.assertEqual(fields[name], original[name])
        self.assertNotIn("${", fields["Depends"])
        self.assertIn("perl:any", fields["Depends"])
        self.assertEqual(package["payload_sha256"], hashlib.sha256(ARGS.archive.read_bytes()).hexdigest())
        for key, path in [("control_sha256", self.debian / "control"), ("changelog_sha256", self.debian / "changelog")]:
            self.assertEqual(receipt["_generated"][key], hashlib.sha256(path.read_bytes()).hexdigest())
        with tarfile.open(ARGS.control) as control:
            members = {m.name.removeprefix("./"): m for m in control if m.isfile()}
            self.assertIn("control", members)
            self.assertFalse(set(members) & {"postinst", "postrm", "preinst", "prerm", "triggers", "conffiles"})
            for name, member in members.items():
                data = control.extractfile(member).read()
                item = package["control_files"][name]
                self.assertEqual(hashlib.sha256(data).hexdigest(), item["sha256"])
                self.assertEqual(member.mode, int(item["mode"], 8))

    def test_native_install_and_debug_elf(self):
        self.assertEqual((self.elf.bits, self.elf.machine), (64, 62))
        self.assertIsNone(self.elf.soname)
        dynamic = run([ARGS.readelf, "--dynamic", self.program]).decode()
        self.assertNotIn("(RPATH)", dynamic)
        self.assertNotIn("(RUNPATH)", dynamic)
        build_dynamic = run([ARGS.readelf, "--dynamic", ARGS.build_binary.absolute()]).decode()
        self.assertRegex(build_dynamic, r"\((RUNPATH|RPATH)\)")
        with tarfile.open(ARGS.symbols) as symbols:
            members = [m for m in symbols if m.isfile()]
            self.assertEqual(len(members), 1)
            member = members[0]
            self.assertEqual((member.uid, member.gid, member.mode), (0, 0, 0o644))
            data = symbols.extractfile(member).read()
        debug = Elf(data)
        self.assertEqual(debug.build_id, self.elf.build_id)
        self.assertEqual(zlib.crc32(data) & 0xffffffff, self.elf.debuglink_crc)
        self.assertEqual(Path(member.name).name, self.elf.debuglink)
        self.assertIn(".debug_info", debug.by_name)
        with tempfile.TemporaryDirectory(dir=os.environ.get("TEST_TMPDIR")) as directory:
            path = Path(directory) / "installed.debug"
            path.write_bytes(data)
            dwarf = run([ARGS.readelf, "--debug-dump=info", path]).decode()
        self.assertIn("DW_TAG_compile_unit", dwarf)
        self.assertRegex(dwarf, r"DW_AT_name\s*:.*\bmain\b")


if __name__ == "__main__":
    unittest.main(argv=[__file__])
