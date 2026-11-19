"""Check the external DHCP relay runtime, symbol and metadata interfaces."""

import hashlib
import json
from pathlib import Path, PurePosixPath
import sys
import tarfile
import unittest
import zlib

from elf_metadata import Elf

INPUTS = list(map(Path, sys.argv[1:]))
sys.argv = sys.argv[:1]


class ArchiveContractTest(unittest.TestCase):
    def archive(self, path):
        files = {}
        with tarfile.open(path) as archive:
            for member in archive:
                name = PurePosixPath(member.name)
                self.assertFalse(name.is_absolute() or ".." in name.parts, member.name)
                self.assertTrue(member.isfile() or member.isdir(), member.name)
                self.assertEqual((member.uid, member.gid), (0, 0), member.name)
                # Preserve the shared tar/mtree rules' fixed historical epochs.
                self.assertIn(member.mtime, (0, 946699200, 1672560000), member.name)
                self.assertNotIn("DEBIAN", name.parts)
                if member.isfile():
                    self.assertNotIn(str(name), files)
                    files[str(name)] = (member.mode, archive.extractfile(member).read())
        return files

    def test_both_runtime_symbol_and_metadata_contracts(self):
        self.assertEqual(len(INPUTS), 6)
        for index, binary in enumerate(("dhcp4relay", "dhcp6relay")):
            with self.subTest(binary=binary):
                runtime, debug, metadata = INPUTS[index * 3:index * 3 + 3]
                files = self.archive(runtime)
                installed = "usr/sbin/" + binary
                self.assertEqual(set(files), {installed})
                mode, contents = files[installed]
                self.assertEqual(mode, 0o755)
                elf = Elf(contents)
                self.assertEqual((elf.bits, elf.machine), (64, 62))
                self.assertTrue(elf.build_id)
                self.assertNotIn(".debug_info", elf.by_name)
                self.assertNotIn(".zdebug_info", elf.by_name)
                symbols = self.archive(debug)
                symbol_path = "usr/lib/debug/.build-id/" + elf.build_id[:2] + "/" + elf.build_id[2:] + ".debug"
                self.assertEqual(set(symbols), {symbol_path})
                symbol_mode, symbol_bytes = symbols[symbol_path]
                self.assertEqual(symbol_mode, 0o644)
                symbol_elf = Elf(symbol_bytes)
                self.assertEqual(symbol_elf.build_id, elf.build_id)
                self.assertTrue({".debug_info", ".zdebug_info"} & set(symbol_elf.by_name))
                self.assertEqual(elf.debuglink, PurePosixPath(symbol_path).name)
                self.assertEqual(elf.debuglink_crc, zlib.crc32(symbol_bytes))
                document = json.loads(metadata.read_text())
                self.assertEqual(document["schema"], 1)
                self.assertEqual(document["module"], "sonic-dhcp-relay")
                self.assertEqual(document["architecture"], "amd64")
                package = "sonic-" + binary
                record = document["packages"][package]
                self.assertEqual(record["payload_sha256"], hashlib.sha256(runtime.read_bytes()).hexdigest())
                fields = record["control_fields"]
                self.assertEqual(fields["Package"], package)
                self.assertEqual(fields["Architecture"], "amd64")
                self.assertTrue(fields["Version"])
                self.assertTrue(fields["Depends"])
                self.assertNotIn("${", json.dumps(fields))
                self.assertIn("control", record["control_files"])


if __name__ == "__main__":
    unittest.main()
