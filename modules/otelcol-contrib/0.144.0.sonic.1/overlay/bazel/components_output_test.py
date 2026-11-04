"""Keep the installed component comparison strict except for provider map order."""
from pathlib import Path
import re
import sys
import unittest

from bazel.package_test import normalize_components


class ComponentOutputTest(unittest.TestCase):
    def test_provider_order_only(self):
        prefix, providers = BASELINE.split(b'\nproviders:\n')
        records = re.findall(rb'    - scheme: [^\n]+\n      module: [^\n]+\n', providers)
        self.assertTrue(normalize_components(BASELINE) ==
                        normalize_components(prefix + b'\nproviders:\n' + b''.join(reversed(records))),
                        'Provider ordering changed the normalized report')

    def test_changed_or_malformed_output_is_rejected(self):
        prefix, providers = BASELINE.split(b'\nproviders:\n')
        records = re.findall(rb'    - scheme: [^\n]+\n      module: [^\n]+\n', providers)
        changed = {
            'module version': BASELINE.replace(b'provider/envprovider v1.50.0', b'provider/envprovider v1.50.1'),
            'missing provider': prefix + b'\nproviders:\n' + b''.join(records[1:]),
            'extra provider': BASELINE + b'    - scheme: extra\n      module: extra v1.0.0\n',
            'duplicate scheme': BASELINE + records[0],
            'duplicate field': BASELINE + b'      module: duplicate v1.0.0\n',
            'unknown field': BASELINE + b'      ignored: true\n',
            'duplicate section': BASELINE + b'providers:\n',
            'malformed record': BASELINE.replace(b'    - scheme:', b'    scheme:', 1),
            'stability': BASELINE.replace(b'Stable', b'Unmaintained', 1),
            'component name': BASELINE.replace(b'name: active_directory_ds', b'name: changed_component', 1),
        }
        expected = normalize_components(BASELINE)
        for name, output in changed.items():
            with self.subTest(change=name):
                self.assertTrue(output != BASELINE, 'Negative control did not change the release report')
                try:
                    actual = normalize_components(output)
                except AssertionError:
                    continue
                self.assertTrue(actual != expected, 'Changed report was accepted')


if __name__ == '__main__':
    BASELINE = Path(sys.argv.pop(1)).read_bytes()
    unittest.main()
