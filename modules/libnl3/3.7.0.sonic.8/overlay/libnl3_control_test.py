"""Original SONiC Debhelper control contract, independent of producer metadata."""
import argparse, tarfile, unittest
parser=argparse.ArgumentParser()
parser.add_argument('--control',action='append',default=[])
args,rest=parser.parse_known_args()
CONTROLS=dict(item.split('=',1) for item in args.control)
RUNTIMES={'libnl-3-200':'libnl-3','libnl-genl-3-200':'libnl-genl-3','libnl-route-3-200':'libnl-route-3','libnl-nf-3-200':'libnl-nf-3','libnl-cli-3-200':'libnl-cli-3'}
class ControlTest(unittest.TestCase):
 def test_original_helpers_and_source_package_identity(self):
  self.assertEqual(set(CONTROLS),set(RUNTIMES)|{'libnl-3-dev','libnl-route-3-dev'})
  for package,path in CONTROLS.items():
   with tarfile.open(path,'r:') as archive:
    files={m.name.removeprefix('./'):archive.extractfile(m).read() for m in archive if m.isfile()}
   fields=dict(line.split(': ',1) for line in files['control'].decode().splitlines() if ': ' in line and not line.startswith(' '))
   self.assertEqual(fields['Package'],package)
   self.assertEqual(fields['Version'],'3.7.0-0.2+b1sonic1')
   self.assertIn(fields['Architecture'],('amd64','arm64'))
   self.assertNotIn('${',fields.get('Depends',''))
   if package in RUNTIMES:
    stem=RUNTIMES[package]
    self.assertIn(b'activate-noawait ldconfig',files['triggers'])
    self.assertIn((stem+' 200 ').encode(),files['shlibs'])
    self.assertTrue(files['symbols'].startswith((stem+'.so.200 '+package+' ').encode()))
if __name__=='__main__':unittest.main(argv=[__file__,*rest])
