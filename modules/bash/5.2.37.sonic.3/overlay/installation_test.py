"""Check the patched Bash installation, CLI identity and detached debug pair."""
import gzip
import hashlib
import json
from pathlib import Path
import sys
import tarfile
import unittest
import zlib

from elf_metadata import Elf

ARCHITECTURE = sys.argv.pop()
# ELF e_machine values are defined by the System V x86-64 and AArch64 ABIs.
MACHINE = {"amd64": 62, "arm64": 183}[ARCHITECTURE]
PAYLOAD, SYMBOLS, CONTROL, METADATA, ORIGINAL_INSTALLATION, BUILD_ELF = [Path(value).absolute() for value in sys.argv[1:]]
del sys.argv[1:]


class InstallationTest(unittest.TestCase):
    def test_installed_shell_version_and_plugin_abi(self):
        package = json.loads(METADATA.read_text())["packages"]["bash"]
        fields = package["control_fields"]
        self.assertEqual(fields["Version"], "5.2.37-2")
        self.assertEqual(fields["Architecture"], ARCHITECTURE)
        self.assertEqual(fields["Essential"], "yes")
        self.assertEqual(fields["Multi-Arch"], "foreign")
        self.assertIn("debianutils", fields["Depends"])
        self.assertIn("libtinfo6", fields["Pre-Depends"])
        self.assertTrue(fields["Maintainer"])
        self.assertEqual(package["payload_sha256"], hashlib.sha256(PAYLOAD.read_bytes()).hexdigest())
        with tarfile.open(PAYLOAD) as archive:
            members = {member.name.removeprefix("./"): member for member in archive}
            shell = Elf(archive.extractfile(members["usr/bin/bash"]).read())
            self.assertEqual(shell.machine, MACHINE)
            # ARM's original long-double conversion uses GCC's quad runtime;
            # the fixed ARM libtinfo and glibc linker script require its loader.
            needed = {"libc.so.6", "libtinfo.so.6"}
            if ARCHITECTURE == "arm64":
                needed |= {"libgcc_s.so.1", "ld-linux-aarch64.so.1"}
                self.assertIn("libgcc-s1", fields["Pre-Depends"])
            self.assertEqual(set(shell.needed), needed)
            self.assertTrue({"load_plugins", "free_plugins", "invoke_plugin_on_shell_execve"} <= shell.exports)
            self.assertIsNone(shell.soname)
            dynamic = shell.by_name[".dynamic"]
            tags = [shell.unpack("qQ", offset)[0] for offset in range(dynamic[4], dynamic[4] + dynamic[5], dynamic[9])]
            self.assertFalse({15, 29} & set(tags), "installed Bash must have no build-tree RPATH/RUNPATH")
            self.assertEqual(members["usr/bin/bash"].mode, 0o755)
            self.assertEqual(members["usr/bin/rbash"].linkname, "bash")
            for path in ["etc/bash.bashrc", "etc/skel/.bashrc", "etc/skel/.profile", "etc/skel/.bash_logout", "usr/share/debianutils/shells.d/bash"]:
                self.assertEqual(members[path].mode, 0o644)
    def test_complete_original_documentation_and_release_catalogs(self):
        original = json.loads(ORIGINAL_INSTALLATION.read_text())
        expected = original["resources"]
        with tarfile.open(PAYLOAD) as archive:
            members = {m.name.removeprefix("./"): m for m in archive}
            for path, oracle in expected.items():
                member = members[path]
                self.assertTrue(member.isfile(), path)
                self.assertEqual((member.mode, member.uid, member.gid), (0o644, 0, 0), path)
                contents = archive.extractfile(member).read()
                if oracle["gzip"]:
                    self.assertEqual(contents[:2], b"\x1f\x8b", path)
                    contents = gzip.decompress(contents)
                self.assertEqual(len(contents), oracle["bytes"], path)
                self.assertEqual(hashlib.sha256(contents).hexdigest(), oracle["sha256"], path)
            self.assertEqual({p for p in members if p.startswith("usr/share/locale/") and members[p].isfile()}, {p for p in expected if p.startswith("usr/share/locale/")})
            fixed_paths = {
                "usr/bin/bash", "usr/bin/clear_console", "usr/bin/bashbug", "usr/bin/rbash",
                "etc/bash.bashrc", "etc/skel/.bashrc", "etc/skel/.profile", "etc/skel/.bash_logout",
                "usr/share/debianutils/shells.d/bash", "usr/share/doc/bash/copyright",
                "usr/share/menu/bash", "usr/share/lintian/overrides/bash",
                "usr/share/man/man1/bash.1.gz", "usr/share/man/man1/rbash.1.gz",
                "usr/share/man/man1/bashbug.1.gz", "usr/share/man/man1/clear_console.1.gz",
                "usr/share/man/man7/bash-builtins.7.gz",
            }
            self.assertEqual({p for p, m in members.items() if m.isfile() or m.issym() or m.islnk()}, set(expected) | fixed_paths)
            for path, member in members.items():
                self.assertEqual((member.uid, member.gid), (0, 0), path)
            script_bytes = archive.extractfile(members["usr/bin/bashbug"]).read()
            script = script_bytes.decode()
            cpu, host, hardening = {
                "amd64": ("x86_64", "x86_64-pc-linux-gnu", "-fcf-protection"),
                "arm64": ("aarch64", "aarch64-unknown-linux-gnu", "-mbranch-protection=standard"),
            }[ARCHITECTURE]
            self.assertIn('MACHINE="' + cpu + '"', script)
            self.assertIn('MACHTYPE="' + host + '"', script)
            self.assertIn(hardening, script)
            # Keep the original AMD64 installation oracle for all non-platform
            # bytes. Debian substitutes these fields from target dpkg-buildflags
            # and Autoconf's canonical host, then strips the source prefix maps.
            normalized = script.replace('MACHINE="' + cpu + '"', 'MACHINE="x86_64"').replace(
                'MACHTYPE="' + host + '"', 'MACHTYPE="x86_64-pc-linux-gnu"').replace(
                hardening, "-fcf-protection").encode()
            self.assertEqual(len(normalized), original["bashbug"]["bytes"])
            self.assertEqual(hashlib.sha256(normalized).hexdigest(), original["bashbug"]["sha256"])
            self.assertIn('RELEASE="5.2"', script)
            self.assertIn('PATCHLEVEL="37"', script)
            self.assertIn('CC="gcc"', script)
            self.assertIn('CFLAGS="-g -O2 -Werror=implicit-function-declaration ', script)
            for build_path in ("external/", "bazel-out/", "ffile-prefix-map", "fdebug-prefix-map", "@CFLAGS@", "!PATCHLEVEL!"):
                self.assertNotIn(build_path, script)
        elf = Elf(BUILD_ELF.read_bytes())
        dynamic = elf.by_name[".dynamic"]
        tags = [elf.unpack("qQ", offset)[0] for offset in range(dynamic[4], dynamic[4] + dynamic[5], dynamic[9])]
        self.assertTrue({15, 29} & set(tags), "native build-tree binary keeps its declared runtime search path")

    def test_control_keeps_menu_registration_and_etc_configuration(self):
        with tarfile.open(CONTROL) as archive:
            files = {member.name: member for member in archive}
            self.assertIn(b"update-menus", archive.extractfile(files["postinst"]).read())
            self.assertIn(b"update-menus", archive.extractfile(files["postrm"]).read())
            self.assertEqual(files["postinst"].mode, 0o755)
            self.assertEqual(set(archive.extractfile(files["conffiles"]).read().decode().splitlines()), {
                "/etc/bash.bashrc", "/etc/skel/.bashrc", "/etc/skel/.profile", "/etc/skel/.bash_logout",
            })

    def test_detached_symbols_have_matching_build_id_debuglink_and_dwarf(self):
        with tarfile.open(PAYLOAD) as payload, tarfile.open(SYMBOLS) as symbols:
            members = {member.name.removeprefix("./"): member for member in payload}
            debug = {member.name.removeprefix("./"): member for member in symbols}
            for path in ("usr/bin/bash", "usr/bin/clear_console"):
                elf = Elf(payload.extractfile(members[path]).read())
                name = "usr/lib/debug/.build-id/" + elf.build_id[:2] + "/" + elf.build_id[2:] + ".debug"
                contents = symbols.extractfile(debug[name]).read()
                dwarf = Elf(contents)
                self.assertEqual(dwarf.build_id, elf.build_id)
                self.assertTrue(".zdebug_info" in dwarf.by_name or dwarf.by_name.get(".debug_info", (0, 0, 0))[2] & 0x800, "original dh_strip compresses final DWARF")
                self.assertEqual(zlib.crc32(contents), elf.debuglink_crc)
                self.assertEqual(Path(name).name, elf.debuglink)
                self.assertTrue(any(section in dwarf.by_name for section in (".debug_info", ".zdebug_info")))
                self.assertEqual(debug[name].mode, 0o644)


if __name__ == "__main__":
    unittest.main()
