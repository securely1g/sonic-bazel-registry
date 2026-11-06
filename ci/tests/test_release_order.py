"""Regression tests for registered SONiC Go pseudo-version ordering."""
import json
import unittest

import test_registry_ci as fixtures


class ReleaseOrderingTests(fixtures.FixtureTestCase):
    def test_actual_goyang_pseudo_version_uses_existing_sonic_patch_order(self):
        key = fixtures.registry_ci.release_key
        version = "0.0.0.sonic.1-20200309174518-a00bece872fc"
        self.assertEqual(key(version), key("0.0.0.sonic.1"))
        self.assertLess(key("0.0.0-sonic.1"), key(version))
        self.assertLess(key(version), key("0.0.0.sonic.2"))
        self.assertLess(key("0.0.0.sonic.99"), key("1.0.0"))

    def test_existing_numeric_patch_separator_and_snapshot_keys_are_exact(self):
        key = fixtures.registry_ci.release_key
        for version, expected in (
            ("1.0.0", ((1,), 0, 0)), ("1.2.0", ((1, 2), 0, 0)),
            ("1.0.0.sonic.2", ((1,), 2, 1)), ("1.0.0-sonic.2", ((1,), 2, 0)),
            ("1.0.0-a00bece872fc", ((1,), 0, 0)),
            ("1.0.0.commit-a00bece", ((1,), 0, 0)),
            ("1.0.0.sonic-buildimage", ((1,), 0, 0))):
            with self.subTest(version=version): self.assertEqual(key(version), expected)

    def test_pseudo_versions_use_registration_order_without_timestamp_sorting(self):
        newer = "0.0.0.sonic.1-20260309174518-ffffffffffff"
        older = "0.0.0.sonic.1-20200309174518-a00bece872fc"
        self.entry("alpha", newer); self.entry("alpha", older)
        self.assertEqual(fixtures.registry_ci.latest_presubmits(self.root), {("alpha", older)})
        metadata = self.root / "modules/alpha/metadata.json"
        value = json.loads(metadata.read_text()); value["versions"].reverse()
        metadata.write_text(json.dumps(value))
        self.assertEqual(fixtures.registry_ci.latest_presubmits(self.root), {("alpha", newer)})

    def test_malformed_and_unrelated_suffixes_remain_rejected(self):
        for version in (
            "0.0.0.sonic.1-2020030917451-a00bece872fc",
            "0.0.0.sonic.1-202003091745180-a00bece872fc",
            "0.0.0.sonic.1-20200309174518-a00bece872f",
            "0.0.0.sonic.1-20200309174518-A00BECE872FC",
            "0.0.0.sonic.1-20200309174518-a00bece872fc0",
            "0.0.0.sonic.1-20200309174518-a00bece872fc-extra",
            "0.0.0.sonic.1-snapshot", "0.0.0.unknown.1"):
            with self.subTest(version=version), self.assertRaises(fixtures.registry_ci.RegistryError):
                fixtures.registry_ci.release_key(version)

if __name__ == "__main__":
    unittest.main()
