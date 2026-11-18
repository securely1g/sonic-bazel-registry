"""Check the original Debian installation contract without invoking kdump."""
import argparse
import email
import gzip
import hashlib
import json
from pathlib import Path
import re
import tarfile
import unittest

parser = argparse.ArgumentParser()
for name in ["archive", "metadata", "control", "source-control"]:
    parser.add_argument("--" + name, required=True, type=Path)
args = parser.parse_args()
SOURCE = args.source_control.parent
FILES = {
    "usr/sbin/kdump-config": ("kdump-config.in", 0o755),
    "usr/share/kdump-tools/kdump-tools.conf": ("kdump-tools.conf.in", 0o644),
    "usr/share/kdump-tools/kdump_mem_estimator": ("kdump_mem_estimator", 0o755),
    "etc/kdump/sysctl.conf": ("sysctl.conf", 0o644),
    "etc/kernel/postinst.d/kdump-tools": ("kernel-postinst-generate-initrd", 0o755),
    "etc/kernel/postrm.d/kdump-tools": ("kernel-postrm-delete-initrd", 0o755),
    "etc/default/grub.d/kdump-tools.cfg": ("kdump-tools.grub.default", 0o644),
    "etc/init.d/kdump-tools": ("kdump-tools.init", 0o755),
    "usr/lib/systemd/system/kdump-tools.service": ("kdump-tools.service", 0o644),
    "usr/lib/systemd/system/kdump-tools-dump.service": ("kdump-tools.kdump-tools-dump.service", 0o644),
    "usr/lib/udev/rules.d/50-kdump-tools.rules": ("kdump-tools.udev", 0o644),
    "usr/share/initramfs-tools/hooks/kdump-tools": ("initramfs.hook", 0o755),
    "usr/share/initramfs-tools/scripts/local-bottom/kdump-sysctl": ("initramfs.local-bottom", 0o755),
    "usr/share/doc/kdump-tools/README.Debian": ("kdump-tools.README.Debian", 0o644),
    "usr/share/doc/kdump-tools/copyright": ("copyright", 0o644),
    "usr/share/man/man8/kdump-config.8.gz": ("kdump-config.8", 0o644),
    "usr/share/man/man5/kdump-tools.5.gz": ("kdump-tools.5.in", 0o644),
    "usr/share/doc/kdump-tools/changelog.gz": (None, 0o644),
}
CMDLINE = b"reset_devices systemd.unit=kdump-tools-dump.service nr_cpus=1 irqpoll usbcore.nousb"


class Installation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files = {}
        with tarfile.open(args.archive) as archive:
            cls.members = archive.getmembers()
            for member in cls.members:
                if member.isfile():
                    cls.files[member.name.removeprefix("./")] = archive.extractfile(member).read()
        cls.receipt = json.loads(args.metadata.read_text())
        cls.package = cls.receipt["packages"]["kdump-tools"]

    def test_original_layout_and_resources(self):
        self.assertEqual(set(self.files), set(FILES))
        self.assertTrue(any(m.isdir() and m.name.removeprefix("./").rstrip("/") == "var/lib/kdump" for m in self.members))
        for member in self.members:
            self.assertEqual((member.uid, member.gid, member.mtime), (0, 0, 0))
            if member.isfile():
                self.assertEqual(member.mode, FILES[member.name.removeprefix("./")][1])
        for path, (source, _) in FILES.items():
            if source is None:
                continue
            expected = (SOURCE / source).read_bytes().replace(b"@KDUMP_CMDLINE_APPEND@", CMDLINE)
            actual = self.files[path]
            if path.endswith(".gz"):
                actual = gzip.decompress(actual)
            self.assertEqual(actual, expected, path)
        # Fresh configuration belongs to postinst/ucf, not a shipped default.
        self.assertNotIn("etc/default/kdump-tools", self.files)

    def test_original_native_changelog(self):
        changelog = gzip.decompress(self.files["usr/share/doc/kdump-tools/changelog.gz"])
        original = (SOURCE / "changelog").read_bytes()
        self.assertTrue(changelog.startswith(original.split(b"\n", 1)[0] + b"\n"))
        self.assertIn(b"kdump-tools (1:1.10.7)", changelog)
        # Independent oracle: original locked dh_installchangelogs -pkdump-tools,
        # original control/changelog, compat12 from debhelper-compat, no notrimdch.
        self.assertEqual(hashlib.sha256(changelog).hexdigest(),
                         "a402830ab1f3b7fb0a7fc4cb73a8014d68e381bf580ecbebe8f4242658f93e56")
        # Original dh_installchangelogs trims the long native Debian history.
        self.assertLess(len(changelog), len(original))
        self.assertTrue(changelog.endswith(b"# To read the complete changelog use `apt changelog kdump-tools`.\n"))

    def test_original_control_and_maintainer_scripts(self):
        fields = self.package["control_fields"]
        self.assertEqual(fields["Package"], "kdump-tools")
        self.assertEqual(fields["Version"], "1:1.10.7")
        self.assertEqual(fields["Architecture"], "amd64")
        paragraphs = args.source_control.read_text().strip().split("\n\n")
        source = email.message_from_string(paragraphs[0])
        binary = email.message_from_string(next(p for p in paragraphs if p.startswith("Package: kdump-tools\n")))
        for name in ["Maintainer", "Section", "Priority", "Homepage", "Description", "Recommends"]:
            self.assertEqual(fields.get(name), binary.get(name, source.get(name)), name)
        self.assertNotIn("${", fields["Depends"])
        self.assertIn("kexec-tools", fields["Depends"])
        self.assertEqual(self.package["payload_sha256"], hashlib.sha256(args.archive.read_bytes()).hexdigest())
        with tarfile.open(args.control) as archive:
            members = {m.name.removeprefix("./"): m for m in archive if m.isfile()}
            self.assertTrue({"control", "postinst", "postrm", "preinst", "config", "templates", "conffiles"} <= set(members))
            for name, member in members.items():
                data = archive.extractfile(member).read()
                receipt = self.package["control_files"][name]
                self.assertEqual(hashlib.sha256(data).hexdigest(), receipt["sha256"])
                self.assertEqual(member.mode, int(receipt["mode"], 8))
                if name in ["preinst", "postinst", "postrm", "config"]:
                    original = (SOURCE / ("kdump-tools." + name)).read_bytes()
                    chunks = original.split(b"#DEBHELPER#")
                    if len(chunks) == 1:
                        self.assertEqual(data, original)
                    else:
                        self.assertEqual(len(chunks), 2)
                        self.assertTrue(data.startswith(chunks[0]))
                        self.assertTrue(data.endswith(chunks[1]))
            templates = archive.extractfile(members["templates"]).read()
            self.assertIn(b"Template: kdump-tools/use_kdump", templates)
            self.assertIn(b"Default: true", templates)
            self.assertRegex(templates, rb"(?m)^Description-[a-z]")


if __name__ == "__main__":
    unittest.main(argv=[__file__])
