"""Keep the installed component comparison strict except for provider map order."""
import copy
import json
from pathlib import Path
import re
import sys
import unittest

from bazel.package_test import normalize_components, validate_buildinfo


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
            'module version': BASELINE.replace(b'provider/envprovider v1.71.0', b'provider/envprovider v1.71.1'),
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


class LinkedModuleTest(unittest.TestCase):
    def test_official_buildinfo(self):
        self.assertEqual(validate_buildinfo(BUILDINFO, BUILDINFO)['linked_module_count'], 1087)

    def test_changed_replacements_fail(self):
        for name, field, value in (
            ('github.com/hamba/avro/v2', 'Version', 'v2.33.1'),
            ('github.com/hamba/avro/v2', 'Sum', 'h1:changed'),
            ('go.opentelemetry.io/obi', 'Path', '../unrelated'),
        ):
            with self.subTest(module=name, field=field):
                changed = copy.deepcopy(BUILDINFO)
                module = next(dep for dep in changed['Deps'] if dep['Path'] == name)
                module['Replace'][field] = value
                with self.assertRaises(AssertionError):
                    validate_buildinfo(changed, BUILDINFO)


if __name__ == '__main__':
    BASELINE = Path(sys.argv.pop(1)).read_bytes()
    BUILDINFO = json.loads(Path(sys.argv.pop(1)).read_bytes())
    unittest.main()
