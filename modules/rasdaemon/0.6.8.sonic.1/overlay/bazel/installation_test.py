"""Validate original rasdaemon installation without touching hardware/services."""
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

parser = argparse.ArgumentParser()
for name in ["archive", "metadata", "control", "symbols", "build-binary", "source", "runtime", "perl", "readelf", "pigz"]:
    parser.add_argument("--" + name, type=Path, required=True)
args = parser.parse_args()
SOURCE = args.source.parent
FILES = {
    "usr/sbin/rasdaemon": 0o755,
    "usr/sbin/ras-mc-ctl": 0o755,
    "etc/default/rasdaemon": 0o644,
    "etc/init.d/rasdaemon": 0o755,
    "lib/systemd/system/rasdaemon.service": 0o644,
    "lib/systemd/system/ras-mc-ctl.service": 0o644,
    "usr/share/doc/rasdaemon/copyright": 0o644,
    "usr/share/doc/rasdaemon/README.Debian": 0o644,
    "usr/share/doc/rasdaemon/TODO": 0o644,
    "usr/share/doc/rasdaemon/NEWS.gz": 0o644,
    "usr/share/doc/rasdaemon/README.gz": 0o644,
    "usr/share/doc/rasdaemon/changelog.gz": 0o644,
    "usr/share/doc/rasdaemon/changelog.Debian.gz": 0o644,
    "usr/share/man/man1/rasdaemon.1.gz": 0o644,
    "usr/share/man/man8/ras-mc-ctl.8.gz": 0o644,
}


def run(command, data=None):
    environment = {k: v for k, v in os.environ.items() if not k.startswith("LD_")}
    environment.update(PATH="", LANG="C", LC_ALL="C")
    return subprocess.run(list(map(str, command)), input=data, env=environment, capture_output=True, check=True).stdout


class Installation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = {}
        with tarfile.open(args.archive, "r:") as archive:
            cls.members = archive.getmembers()
            for member in cls.members:
                if member.isfile():
                    cls.payload[member.name.removeprefix("./")] = archive.extractfile(member).read()
        cls.elf = Elf(cls.payload["usr/sbin/rasdaemon"])
        cls.receipt = json.loads(args.metadata.read_text())
        cls.runtime = args.runtime.absolute()

    def test_original_payload_templates_and_docs(self):
        self.assertEqual(set(self.payload), set(FILES))
        self.assertTrue(any(m.isdir() and m.name.removeprefix("./").rstrip("/") == "etc/ras/dimm_labels.d" for m in self.members))
        for member in self.members:
            self.assertEqual((member.uid, member.gid, member.mtime), (0, 0, 0))
            if member.isfile():
                self.assertEqual(member.mode, FILES[member.name.removeprefix("./")])
        for path, source in {
            "etc/default/rasdaemon": "misc/rasdaemon.env",
            "etc/init.d/rasdaemon": "debian/rasdaemon.init",
            "usr/share/doc/rasdaemon/copyright": "debian/copyright",
            "usr/share/doc/rasdaemon/README.Debian": "debian/README.Debian",
            "usr/share/doc/rasdaemon/TODO": "TODO",
        }.items():
            self.assertEqual(self.payload[path], (SOURCE / source).read_bytes(), path)
        for unit in ["rasdaemon", "ras-mc-ctl"]:
            expected = (SOURCE / ("misc/" + unit + ".service.in")).read_bytes().replace(b"@sbindir@", b"/usr/sbin").replace(b"@SYSCONFDEFDIR@", b"/etc/default")
            self.assertEqual(self.payload["lib/systemd/system/" + unit + ".service"], expected)
        script = (SOURCE / "util/ras-mc-ctl.in").read_bytes()
        for key, value in {"prefix": "/usr", "sysconfdir": "/etc", "RAS_DB_FNAME": "ras-mc_event.db", "RASSTATEDIR": "/var/lib/rasdaemon"}.items():
            script = script.replace(("@" + key + "@").encode(), value.encode())
        for feature in ["AER", "MCE", "EXTLOG"]:
            script = script.replace(("@WITH_" + feature + "_TRUE@").encode(), b"")
        for feature in ["ARM", "DEVLINK", "DISKERROR", "MEMORY_FAILURE"]:
            script = script.replace(("@WITH_" + feature + "_TRUE@").encode(), b"#")
        self.assertEqual(self.payload["usr/sbin/ras-mc-ctl"], script)
        run([args.perl, "-c", self.runtime / "usr/sbin/ras-mc-ctl"])
        for output, original in [("NEWS.gz", "NEWS"), ("README.gz", "README"), ("changelog.gz", "ChangeLog")]:
            self.assertEqual(run([args.pigz, "-dc"], self.payload["usr/share/doc/rasdaemon/" + output]), (SOURCE / original).read_bytes())
        history = run([args.pigz, "-dc"], self.payload["usr/share/doc/rasdaemon/changelog.Debian.gz"])
        # Independent original dh_installchangelogs, original0.6.8-1
        # control/changelog/compat12, no helper overrides, original ChangeLog.
        self.assertEqual(len(history), 3500)
        self.assertEqual(hashlib.sha256(history).hexdigest(), "ebe3403e93142df1dc7574e716b1e8d1b4067676b6978236f404fafa079e8d05")
        for output, original in [("usr/share/man/man1/rasdaemon.1.gz", "man/rasdaemon.1.in"), ("usr/share/man/man8/ras-mc-ctl.8.gz", "man/ras-mc-ctl.8.in")]:
            expected = (SOURCE / original).read_bytes().replace(b"@META_ALIAS@", b"").replace(b"@META_DATE@", b"").replace(b"@sysconfdir@", b"/etc")
            self.assertEqual(run([args.pigz, "-dc"], self.payload[output]), expected)

    def test_original_control_and_effect_scripts(self):
        package = self.receipt["packages"]["rasdaemon"]
        fields = package["control_fields"]
        self.assertEqual((fields["Package"], fields["Version"], fields["Architecture"]), ("rasdaemon", "0.6.8-1", "amd64"))
        paragraphs = (SOURCE / "debian/control").read_text().strip().split("\n\n")
        source = email.message_from_string(paragraphs[0])
        original = email.message_from_string(next(p for p in paragraphs if p.startswith("Package: rasdaemon\n")))
        for name in ["Maintainer", "Section", "Priority", "Homepage", "Description"]:
            self.assertEqual(fields.get(name), original.get(name, source.get(name)), name)
        self.assertNotIn("${", fields["Depends"])
        for name in ["libsqlite3-0", "sqlite3", "libdbd-sqlite3-perl", "perl"]:
            self.assertIn(name, fields["Depends"])
        self.assertEqual(package["payload_sha256"], hashlib.sha256(args.archive.read_bytes()).hexdigest())
        with tarfile.open(args.control) as archive:
            members = {m.name.removeprefix("./"): m for m in archive if m.isfile()}
            self.assertTrue({"control", "conffiles", "postinst", "postrm", "prerm"} <= set(members))
            for name, member in members.items():
                data = archive.extractfile(member).read()
                entry = package["control_files"][name]
                self.assertEqual(hashlib.sha256(data).hexdigest(), entry["sha256"])
                self.assertEqual(member.mode, int(entry["mode"], 8))
            postrm = archive.extractfile(members["postrm"]).read()
            before, after = (SOURCE / "debian/rasdaemon.postrm").read_bytes().split(b"#DEBHELPER#")
            self.assertTrue(postrm.startswith(before))
            self.assertTrue(postrm.endswith(after))
            postinst = archive.extractfile(members["postinst"]).read()
            self.assertIn(b"rasdaemon.service", postinst)
            self.assertIn(b"ras-mc-ctl.service", postinst)
            conffiles = archive.extractfile(members["conffiles"]).read().decode().splitlines()
            self.assertEqual(set(conffiles), {"/etc/default/rasdaemon", "/etc/init.d/rasdaemon"})

    def test_installed_runtime_and_matching_debug_elf(self):
        self.assertEqual((self.elf.bits, self.elf.machine), (64, 62))
        self.assertIsNone(self.elf.soname)
        self.assertIn("libsqlite3.so.0", self.elf.needed)
        self.assertIn("libc.so.6", self.elf.needed)
        self.assertIn(b"rasdaemon 0.6.8", run([self.runtime / "bin/rasdaemon", "--version"]))
        program = self.runtime / "usr/sbin/rasdaemon"
        self.assertEqual(program.read_bytes(), self.payload["usr/sbin/rasdaemon"])
        installed = run([args.readelf, "--dynamic", program]).decode()
        self.assertNotRegex(installed, r"\((RPATH|RUNPATH)\)")
        build = run([args.readelf, "--dynamic", args.build_binary.absolute()]).decode()
        self.assertRegex(build, r"\((RPATH|RUNPATH)\)")
        manifest = json.loads((self.runtime / "toolchain.json").read_text())
        libraries = os.pathsep.join(str(self.runtime / name) for name in manifest["library_directories"])
        listing = run([self.runtime / manifest["loader"], "--inhibit-cache", "--library-path", libraries, "--list", program]).decode()
        declared = {p.resolve() for name in manifest["library_directories"] for p in (self.runtime / name).glob("*.so*") if p.is_file()}
        for path in re.findall(r"=>\s+(/\S+)", listing):
            self.assertIn(Path(path).resolve(), declared)
        with tarfile.open(args.symbols) as archive:
            members = [m for m in archive if m.isfile()]
            self.assertEqual(len(members), 1)
            member = members[0]
            self.assertEqual((member.uid, member.gid, member.mode), (0, 0, 0o644))
            data = archive.extractfile(member).read()
        debug = Elf(data)
        self.assertEqual(debug.build_id, self.elf.build_id)
        self.assertEqual(zlib.crc32(data) & 0xffffffff, self.elf.debuglink_crc)
        self.assertEqual(Path(member.name).name, self.elf.debuglink)
        self.assertIn(".debug_info", debug.by_name)
        with tempfile.TemporaryDirectory(dir=os.environ.get("TEST_TMPDIR")) as directory:
            path = Path(directory) / "rasdaemon.debug"
            path.write_bytes(data)
            information = run([args.readelf, "--debug-dump=info", "--wide", path]).decode()
            self.assertIn("DW_TAG_compile_unit", information)
            self.assertIn("rasdaemon.c", information)


if __name__ == "__main__":
    unittest.main(argv=[__file__])
