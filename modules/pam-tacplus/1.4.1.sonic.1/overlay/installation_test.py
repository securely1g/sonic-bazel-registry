"""Original SONiC libtac/PAM installation, shared ABI and package controls."""
import gzip
import hashlib
import json
from pathlib import Path
import sys
import tarfile
import unittest
import zlib
from elf_metadata import Elf

LIBRARY, PAM, LIBDEBUG, PAMDEBUG, LIBCONTROL, PAMCONTROL, METADATA, PROFILE, DEV, CHANGELOG, README, HEAD1, HEAD2, HEAD3, HEAD4 = [Path(p) for p in sys.argv[1:]]
del sys.argv[1:]

def members(archive):
    return {member.name.removeprefix("./"):member for member in archive}

class Installation(unittest.TestCase):
    def test_original_runtime_namespace_and_abi(self):
        with tarfile.open(LIBRARY) as archive:
            files=members(archive)
            for name in ["libtac","libtacsupport"]:
                path="usr/lib/x86_64-linux-gnu/"+name+".so.2.0.0"
                member=files[path]
                self.assertEqual((member.mode,member.uid,member.gid),(0o644,0,0))
                elf=Elf(archive.extractfile(member).read())
                self.assertEqual((elf.machine,elf.soname),(62,name+".so.2"))
                self.assertEqual(files[path.removesuffix(".0.0")].linkname,name+".so.2.0.0")
                if name=="libtacsupport":
                    self.assertNotIn("libtac.so.2",elf.needed,"the original support .la has no libtac LIBADD")
                    self.assertIn("parse_config_file",elf.exports)
        with tarfile.open(PAM) as archive:
            files=members(archive);member=files["lib/x86_64-linux-gnu/security/pam_tacplus.so"]
            self.assertEqual((member.mode,member.uid,member.gid),(0o644,0,0))
            elf=Elf(archive.extractfile(member).read())
            self.assertIn("libtac.so.2",elf.needed)
            self.assertTrue({"pam_sm_authenticate","pam_sm_acct_mgmt","pam_sm_open_session","pam_sm_close_session"}<=elf.exports)
            self.assertEqual(archive.extractfile(files["usr/share/pam-configs/tacplus"]).read(),PROFILE.read_bytes())

    def test_real_control_projection_and_ldconfig_trigger(self):
        for payload,control,name in [(LIBRARY,LIBCONTROL,"libtac2"),(PAM,PAMCONTROL,"libpam-tacplus")]:
            package=json.loads(METADATA.read_text())["packages"][name]
            self.assertEqual(package["payload_sha256"],hashlib.sha256(payload.read_bytes()).hexdigest())
            with tarfile.open(control) as archive:
                files=members(archive);fields=archive.extractfile(files["control"]).read().decode()
                self.assertIn("Package: "+name+"\n",fields)
                self.assertIn("Version: 1.4.1-1\n",fields)
                if name=="libtac2":
                    self.assertIn(b"activate-noawait ldconfig",archive.extractfile(files["triggers"]).read())
                else:
                    self.assertIn(b"pam-auth-update --package",archive.extractfile(files["postinst"]).read())
                    self.assertEqual(files["postinst"].mode,0o755)

    def test_original_docs_and_development_installation(self):
        # Expected trimmed bytes independently projected by compat9 Debian helpers
        # from the original v1.4.1-1 packaging; each binary package gets its own title.
        expected = {"libtac2": "fa167bb34892825c7307222f6dfdcc3dc95bb46364c969208bd40dd8adb040e0", "libpam-tacplus": "2ca3a1ff80ac33a428cd262234664dd185ae3bed489fdc7b8a8dd4e83b045b22", "libtac-dev": "ed4b2fdadbd306332c67154c7afcbdcca997b8950ea643c4f9754f5743b313e9"}
        for payload, package in [(LIBRARY, "libtac2"), (PAM, "libpam-tacplus"), (DEV, "libtac-dev")]:
            with tarfile.open(payload) as archive:
                files = members(archive)
                prefix = "usr/share/doc/" + package + "/"
                for basename in ["changelog.gz", "changelog.Debian.gz"]:
                    member = files[prefix + basename]
                    self.assertEqual((member.mode, member.uid, member.gid), (0o644, 0, 0))
                    compressed = archive.extractfile(member).read()
                    self.assertEqual(compressed[8], 2)  # original dh_compress -9
                    raw = gzip.decompress(compressed)
                    if basename == "changelog.gz": self.assertEqual(raw, CHANGELOG.read_bytes())
                    else: self.assertEqual(hashlib.sha256(raw).hexdigest(), expected[package])
                if package == "libpam-tacplus":
                    self.assertEqual(gzip.decompress(archive.extractfile(files[prefix + "README.md.gz"]).read()), README.read_bytes())
                else: self.assertNotIn(prefix + "README.md.gz", files)
        with tarfile.open(DEV) as archive:
            files = members(archive)
            for name, source in zip(["cdefs.h", "libtac.h", "tacplus.h", "support.h"], [HEAD1, HEAD2, HEAD3, HEAD4]):
                member = files["usr/include/libtac/" + name]
                self.assertEqual((member.mode, member.uid, member.gid), (0o644, 0, 0))
                self.assertEqual(archive.extractfile(member).read(), source.read_bytes())
            for name in ["libtac", "libtacsupport"]:
                self.assertEqual(files["usr/lib/x86_64-linux-gnu/" + name + ".so"].linkname, name + ".so.2.0.0")
            pc = archive.extractfile(files["usr/lib/x86_64-linux-gnu/pkgconfig/libtac.pc"]).read().decode()
            self.assertIn("Version: 1.4.1\n", pc)
            self.assertIn("Libs: -L${libdir} -ltac\n", pc)
            self.assertIn("Cflags: -I${includedir}\n", pc)

    def test_dh_strip_debug_pair(self):
        for payload,debug in [(LIBRARY,LIBDEBUG),(PAM,PAMDEBUG)]:
            with tarfile.open(payload) as data,tarfile.open(debug) as symbols:
                files=members(data);debugfiles=members(symbols)
                for path,member in files.items():
                    if not member.isfile():continue
                    contents=data.extractfile(member).read()
                    if not contents.startswith(b"\x7fELF"):continue
                    elf=Elf(contents);name="usr/lib/debug/.build-id/"+elf.build_id[:2]+"/"+elf.build_id[2:]+".debug"
                    body=symbols.extractfile(debugfiles[name]).read();dwarf=Elf(body)
                    self.assertEqual(dwarf.build_id,elf.build_id)
                    section = dwarf.by_name.get(".debug_info", dwarf.by_name.get(".zdebug_info"))
                    self.assertIsNotNone(section)
                    self.assertGreater(len(dwarf.section_data(section)), 24)
                    self.assertEqual(zlib.crc32(body),elf.debuglink_crc)
                    self.assertTrue(".zdebug_info" in dwarf.by_name or dwarf.by_name.get(".debug_info",(0,0,0))[2]&0x800)

if __name__=="__main__":unittest.main()
