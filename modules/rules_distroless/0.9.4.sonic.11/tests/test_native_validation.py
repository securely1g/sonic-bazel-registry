"""Keep native and source-preservation failures visible in registry validation."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    'locked_import_validation', Path(__file__).resolve().parents[1] / 'validate_native.py')
validation = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validation)


class NativeValidationTests(unittest.TestCase):
    def test_wrong_userspace_is_rejected_even_on_matching_host(self):
        with patch.object(validation.platform, 'system', return_value='Linux'), \
             patch.object(validation.platform, 'machine', return_value='x86_64'), \
             patch.object(validation.subprocess, 'check_output', return_value='arm64\n'):
            with self.assertRaisesRegex(ValueError, 'userspace'):
                validation.verify_native('amd64')

    def test_foreign_host_is_rejected_even_with_matching_userspace(self):
        with patch.object(validation.platform, 'system', return_value='Linux'), \
             patch.object(validation.platform, 'machine', return_value='x86_64'), \
             patch.object(validation.subprocess, 'check_output', return_value='arm64\n'):
            with self.assertRaisesRegex(ValueError, 'native Linux host'):
                validation.verify_native('arm64')

    def run_with_command(self, root, command):
        entry, artifacts = root / 'recipe', root / 'artifacts'
        entry.mkdir()
        (entry / 'input').write_text('reviewed source')
        with patch.object(validation, 'ROOT', root), \
             patch.object(validation, 'verify_native', return_value={'machine': 'fixture'}), \
             patch.object(validation, 'regenerate_fixture', return_value='fixture-sha256'):
            validation.validate(entry, artifacts, 'amd64', command, source_head='fixture')

    def test_source_mutation_fails_and_is_recorded(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            command = [sys.executable, '-c', 'from pathlib import Path; import sys; Path(sys.argv[1]).write_text("changed")',
                       str(root / 'recipe/input')]
            with self.assertRaisesRegex(ValueError, 'source inputs changed'):
                self.run_with_command(root, command)
            receipt = json.loads((root / 'artifacts/locked-import-validation.json').read_text())
            self.assertFalse(receipt['source_inputs_unchanged'])
            self.assertEqual(receipt['result'], 'failed: recipe inputs changed')

    def test_failed_test_keeps_failure_and_source_receipt(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaises(subprocess.CalledProcessError):
                self.run_with_command(root, [sys.executable, '-c', 'raise SystemExit(7)'])
            receipt = json.loads((root / 'artifacts/locked-import-validation.json').read_text())
            self.assertTrue(receipt['source_inputs_unchanged'])
            self.assertEqual(receipt['result'], 'incomplete')


if __name__ == '__main__':
    unittest.main()
