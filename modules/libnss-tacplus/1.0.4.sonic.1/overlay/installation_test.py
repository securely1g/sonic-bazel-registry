"""Original NSS hook target-libc filename, public ABI and source controls."""
from pathlib import Path
import sys,tarfile,unittest
import gzip,hashlib,json,zlib
from elf_metadata import Elf
PAYLOAD,CONTROL,CONFIG,DEBUG,NATIVE,INSTALL,CHANGELOG,METADATA=map(Path,sys.argv[1:]);del sys.argv[1:]
class Installation(unittest.TestCase):
 def test_original_hook(self):
  with tarfile.open(PAYLOAD) as a:
   files={m.name.removeprefix("./"):m for m in a};link=files["lib/x86_64-linux-gnu/libnss_tacplus.so.2"]
   self.assertTrue(link.issym());self.assertEqual(link.linkname,"libnss_tacplus-.so")
   binary=files["lib/x86_64-linux-gnu/"+link.linkname];self.assertEqual((binary.mode,binary.uid,binary.gid),(0o755,0,0))
   elf=Elf(a.extractfile(binary).read());self.assertEqual(elf.soname,"libnss_tacplus.so.2");self.assertIn("_nss_tacplus_getpwnam_r",elf.exports);self.assertIn("libtac.so.2",elf.needed)
   self.assertEqual(a.extractfile(files["etc/tacplus_nss.conf"]).read(),CONFIG.read_bytes())
   self.assertNotIn("lib/x86_64-linux-gnu/libnss_tacplus.la",files)
  with tarfile.open(CONTROL) as a:
   files={m.name.removeprefix("./"):m for m in a};self.assertIn(b"Package: libnss-tacplus\n",a.extractfile(files["control"]).read());self.assertIn(b"activate-noawait ldconfig",a.extractfile(files["triggers"]).read());self.assertIn(b"nsswitch.conf",a.extractfile(files["postinst"]).read())
 def test_original_install_strip_and_symbol_only_dbgsym(self):
  # Original install-data-hook strips before compat9 dh_strip extracts dbgsym.
  native=Elf(NATIVE.read_bytes());hook=Elf(INSTALL.read_bytes())
  self.assertIn(".debug_info",native.by_name)
  self.assertGreater(len(native.section_data(native.by_name[".debug_info"])),24)
  self.assertFalse(any(n.startswith((".debug_",".zdebug_")) for n in hook.by_name))
  self.assertIn(".symtab",hook.by_name)
  def symbols(elf):
   table=elf.by_name[".symtab"];strings=elf.section_data(elf.sections[table[6]])
   return {elf.string(strings,elf.unpack("I",offset)[0]) for offset in range(table[4],table[4]+table[5],table[9])}
  self.assertIn("_nss_tacplus_getpwnam_r",symbols(hook))
  with tarfile.open(PAYLOAD) as data,tarfile.open(DEBUG) as debug:
   files={m.name.removeprefix("./"):m for m in data};link=files["lib/x86_64-linux-gnu/libnss_tacplus.so.2"]
   elf=Elf(data.extractfile(files["lib/x86_64-linux-gnu/"+link.linkname]).read())
   self.assertNotIn(".symtab",elf.by_name)
   self.assertNotIn(".comment",elf.by_name);self.assertNotIn(".note",elf.by_name)
   self.assertIn(".note.gnu.build-id",elf.by_name);self.assertIn(".gnu_debuglink",elf.by_name)
   self.assertNotIn("_nss_tacplus_getpwuid_r",elf.exports)
   expected="usr/lib/debug/.build-id/"+elf.build_id[:2]+"/"+elf.build_id[2:]+".debug"
   debugfiles={m.name.removeprefix("./"):m for m in debug}
   member=debugfiles[expected];body=debug.extractfile(member).read();sym=Elf(body)
   self.assertEqual((member.mode,member.uid,member.gid),(0o644,0,0))
   self.assertEqual(sym.build_id,elf.build_id);self.assertEqual(zlib.crc32(body),elf.debuglink_crc)
   self.assertFalse(any(n.startswith((".debug_",".zdebug_")) for n in sym.by_name))
   self.assertIn("_nss_tacplus_getpwnam_r",symbols(sym))
   self.assertIn(".comment",sym.by_name)

 def test_original_docs_and_metadata(self):
  with tarfile.open(PAYLOAD) as a:
   files={m.name.removeprefix("./"):m for m in a};prefix="usr/share/doc/libnss-tacplus/"
   for basename in ["changelog.gz","changelog.Debian.gz"]:
    member=files[prefix+basename];self.assertEqual((member.mode,member.uid,member.gid),(0o644,0,0))
    compressed=a.extractfile(member).read();self.assertEqual(compressed[8],2)
    raw=gzip.decompress(compressed)
    if basename=="changelog.gz":self.assertEqual(raw,CHANGELOG.read_bytes())
    else:self.assertEqual(hashlib.sha256(raw).hexdigest(),"7007520bead5431da01deb87662916f88291f6f4f4cd258043dfab6b85695460")
   self.assertNotIn(prefix+"README",files);self.assertNotIn(prefix+"README.gz",files)
  record=json.loads(METADATA.read_text())["packages"]["libnss-tacplus"]
  self.assertEqual(record["payload_sha256"],hashlib.sha256(PAYLOAD.read_bytes()).hexdigest())
  with tarfile.open(CONTROL) as a:
   files={m.name.removeprefix("./"):m for m in a}
   self.assertIn(b"Version: 1.0.4-1\n",a.extractfile(files["control"]).read())
   self.assertIn(b"_nss_tacplus_getpwnam_r@Base 1.0.1",a.extractfile(files["symbols"]).read())

if __name__=="__main__":unittest.main()
