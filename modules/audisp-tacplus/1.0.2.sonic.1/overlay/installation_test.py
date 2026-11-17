"""Original audit plugin entry point, configuration and maintainer effects."""
from pathlib import Path
import sys,tarfile,unittest,gzip,zlib
from elf_metadata import Elf
PAYLOAD,CONTROL,CONFIG,RULES,DEBUG,MAN,README,NEWS,CHANGELOG=map(Path,sys.argv[1:]);del sys.argv[1:]
class Installation(unittest.TestCase):
 def test_original_installation(self):
  with tarfile.open(PAYLOAD) as a:
   files={m.name.removeprefix("./"):m for m in a};binary=files["sbin/audisp-tacplus"];self.assertEqual((binary.mode,binary.uid,binary.gid),(0o755,0,0));elf=Elf(a.extractfile(binary).read());self.assertTrue({"libtac.so.2","libtacsupport.so.2","libauparse.so.0"}<=set(elf.needed))
   for name,src in [("etc/audit/plugins.d/audisp-tacplus.conf",CONFIG),("etc/audit/rules.d/audisp-tacplus.rules",RULES)]:self.assertEqual(a.extractfile(files[name]).read(),src.read_bytes());self.assertEqual(files[name].mode,0o644)
  with tarfile.open(CONTROL) as a:
   files={m.name.removeprefix("./"):m for m in a};self.assertIn(b"Package: audisp-tacplus\n",a.extractfile(files["control"]).read());post=a.extractfile(files["postinst"]).read();self.assertIn(b"augenrules",post);self.assertIn(b"auditd",post)
 def test_original_compressed_documents_and_native_changelog(self):
  with tarfile.open(PAYLOAD) as a:
   files={m.name.removeprefix("./"):m for m in a}
   for path,source in [("usr/share/man/man8/audisp-tacplus.8.gz",MAN),("usr/share/doc/audisp-tacplus/README.gz",README),("usr/share/doc/audisp-tacplus/NEWS.gz",NEWS),("usr/share/doc/audisp-tacplus/changelog.gz",CHANGELOG)]:
    member=files[path];data=a.extractfile(member).read()
    # Native version1.0.2 and compat9 retain the original Debian changelog,
    # installed as changelog; no upstream ChangeLog is independently selected.
    self.assertEqual(gzip.decompress(data),source.read_bytes())
    self.assertEqual(data[4:8],b"\0"*4)
    self.assertEqual((member.mode,member.uid,member.gid),(0o644,0,0))
   self.assertNotIn("usr/share/doc/audisp-tacplus/changelog.Debian.gz",files)
   self.assertNotIn("usr/share/doc/audisp-tacplus/ChangeLog.gz",files)
  with tarfile.open(CONTROL) as a:
   files={m.name.removeprefix("./"):m for m in a}
   self.assertIn(b"Version: 1.0.2\n",a.extractfile(files["control"]).read())
   self.assertIn(b"augenrules",a.extractfile(files["postrm"]).read())
 def test_matching_compressed_debug_symbols(self):
  with tarfile.open(PAYLOAD) as a:
   runtime=Elf(a.extractfile(next(m for m in a if m.name.removeprefix("./")=="sbin/audisp-tacplus")).read())
  with tarfile.open(DEBUG) as a:
   files={m.name.removeprefix("./"):m for m in a}
   symbols=[a.extractfile(m).read() for m in files.values() if m.isfile()]
   symbols=[d for d in symbols if d.startswith(b"\x7fELF")]
   self.assertEqual(len(symbols),1)
   debug=Elf(symbols[0]);self.assertEqual(runtime.build_id,debug.build_id)
   self.assertEqual(runtime.debuglink_crc,zlib.crc32(symbols[0])&0xffffffff)
   self.assertIn(".debug_info",debug.by_name)
   self.assertGreater(debug.by_name[".debug_info"][5],0)
   self.assertTrue(debug.by_name[".debug_info"][2]&0x800)
   self.assertNotIn(".debug_info",runtime.by_name)
   link=files["usr/share/doc/audisp-tacplus-dbgsym"]
   self.assertTrue(link.issym());self.assertEqual(link.linkname,"audisp-tacplus")
if __name__=="__main__":unittest.main()
