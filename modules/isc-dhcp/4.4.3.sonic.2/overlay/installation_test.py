"""Original relay resources, Debian controls and split ELF debug contract."""
import gzip
from pathlib import Path
import sys
import tarfile
import unittest
import zlib
from elf_metadata import Elf

PAYLOAD, DEBUG, CONTROL, INIT, MAN, README, RELNOTES = map(Path, sys.argv[1:])
del sys.argv[1:]

def files(path):
    with tarfile.open(path) as archive:
        return {m.name.removeprefix('./'): (m, archive.extractfile(m).read() if m.isfile() else None) for m in archive}

class RelayInstallation(unittest.TestCase):
    def test_original_relay_payload(self):
        payload = files(PAYLOAD)
        expected = {
            'etc/init.d/isc-dhcp-relay': INIT.read_bytes(),
            'usr/share/doc/isc-dhcp-relay/README.gz': README.read_bytes(),
            'usr/share/doc/isc-dhcp-relay/changelog.gz': RELNOTES.read_bytes(),
        }
        man = MAN.read_bytes()
        for old, new in [(b'ETCDIR', b'/etc/dhcp'), (b'RUNDIR', b'/var/run'), (b'CLIENTBINDIR', b'/sbin'), (b'DBDIR', b'/var/lib/dhcp')]:
            man = man.replace(old, new)
        expected['usr/share/man/man8/dhcrelay.8.gz'] = man
        for path, content in expected.items():
            info, data = payload[path]
            self.assertEqual(gzip.decompress(data) if path.endswith('.gz') else data, content)
            self.assertEqual((info.uid, info.gid, info.mode), (0, 0, 0o644 if path.endswith('.gz') else 0o755))
        for name in ['changelog.Debian.gz', 'NEWS.Debian.gz']:
            self.assertTrue(gzip.decompress(payload['usr/share/doc/isc-dhcp-relay/' + name][1]))
        self.assertIn('usr/share/doc/isc-dhcp-relay/copyright', payload)
        self.assertNotIn('usr/sbin/dhcpd', payload)
        self.assertNotIn('sbin/dhclient', payload)

    def test_runtime_and_debug_identity(self):
        payload = files(PAYLOAD)
        info, data = payload['usr/sbin/dhcrelay']
        self.assertEqual((info.uid, info.gid, info.mode), (0, 0, 0o755))
        runtime = Elf(data)
        debug_files = files(DEBUG)
        doc_link = debug_files['usr/share/doc/isc-dhcp-relay-dbgsym'][0]
        self.assertTrue(doc_link.issym())
        self.assertEqual(doc_link.linkname, 'isc-dhcp-relay')
        symbols = [data for info, data in debug_files.values() if info.isfile() and data.startswith(b'\x7fELF')]
        self.assertEqual(len(symbols), 1)
        debug = Elf(symbols[0])
        self.assertEqual(runtime.build_id, debug.build_id)
        self.assertEqual(runtime.debuglink_crc, zlib.crc32(symbols[0]) & 0xffffffff)
        self.assertIn('.debug_info', debug.by_name)
        self.assertGreater(debug.by_name['.debug_info'][5], 0)
        self.assertNotIn('.debug_info', runtime.by_name)

    def test_original_control_effects_are_delivered(self):
        control = files(CONTROL)
        self.assertIn(b'Package: isc-dhcp-relay\n', control['control'][1])
        self.assertIn(b'Version: 4.4.3-P1-2\n', control['control'][1])
        self.assertIn(b'Architecture: amd64\n', control['control'][1])
        for name in ['postinst', 'postrm', 'prerm', 'config', 'templates', 'conffiles']:
            self.assertIn(name, control)
        self.assertIn(b'/etc/default/isc-dhcp-relay', control['postinst'][1])
        self.assertIn(b'/etc/init.d/isc-dhcp-relay', control['conffiles'][1])
        self.assertIn(b'isc-dhcp-relay/servers', control['templates'][1])

if __name__ == '__main__':
    unittest.main()
