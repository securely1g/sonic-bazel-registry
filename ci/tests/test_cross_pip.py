"""Guard cross-wheel selection against dependency and source changes."""

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock


def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parents[1] / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pip = load("cross_pip")
toolchains = load("cross_toolchain")
SOURCE = '''
module(name="example", version="1.0")
pip = use_extension("@rules_python//python/extensions:pip.bzl", "pip")
pip.parse(hub_name="example_pip", python_version="3.13", requirements_lock="//python:requirements.txt")
'''


class CrossPipTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.source = self.root / "modules/example/1.0"
        self.source.mkdir(parents=True)
        (self.source / "MODULE.bazel").write_text(SOURCE)
        (self.source / "python").mkdir()
        self.lock = self.source / "python/requirements.txt"
        self.lock.write_text("cffi==1.17.1 --hash=sha256:" + "a" * 64 + "\n")
        self.consumer = self.root / "consumer"
        self.consumer.mkdir()
        (self.consumer / "MODULE.bazel").write_text('module(name="consumer")\n')
        self.artifacts = self.root / "artifacts"
        self.artifacts.mkdir()
        self.versions = {"example": "1.0", "rules_python": "1.9.0"}

    def prepare(self, versions=None):
        with mock.patch.object(toolchains, "module_graph", return_value=versions or self.versions):
            return pip.prepare(self.root, self.consumer, self.artifacts, ["bazel"], [],
                               self.versions, toolchains)

    def test_original_requirements_and_native_target_resolution_are_preserved(self):
        original = self.lock.read_bytes()
        receipt = self.prepare()
        generated = (self.consumer / "MODULE.bazel").read_text()
        self.assertIn('version="1.9.0"', generated)
        self.assertIn("requirements_lock='@example//python:requirements.txt'", generated)
        self.assertIn("experimental_index_url='https://pypi.org/simple'", generated)
        self.assertNotIn("experimental_target_platforms", generated)
        pip.record_locks(receipt, self.root, self.artifacts, lambda *_: [self.source / "MODULE.bazel"])
        evidence = self.artifacts / receipt["hubs"][0]["lock_evidence"]
        self.assertEqual(evidence.read_bytes(), original)
        self.assertEqual(self.lock.read_bytes(), original)
        self.assertEqual((self.source / "MODULE.bazel").read_text(), SOURCE)
        self.assertEqual(json.loads((self.artifacts / "cross-pip-hubs.json").read_text()), receipt)

    def test_dependency_upgrade_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "changed the consumer"):
            self.prepare({**self.versions, "rules_python": "2.0.0"})

    def test_development_and_explicit_platform_hubs_keep_their_configuration(self):
        self.assertEqual(pip.simple_hubs(SOURCE.replace('"pip")', '"pip", dev_dependency=True)')), [])
        self.assertEqual(pip.simple_hubs(SOURCE.replace(
            'requirements_lock="//python:requirements.txt"',
            'requirements_by_platform={"//:arm.txt": "linux_aarch64"}')), [])
        self.assertEqual(pip.simple_hubs(SOURCE.replace(
            'requirements_lock="//python:requirements.txt"',
            'requirements_lock="//python:requirements.txt", experimental_index_url="https://example.test/simple"')), [])
        with self.assertRaisesRegex(ValueError, "literal"):
            pip.simple_hubs(SOURCE.replace('"3.13"', 'unknown_version'))

    def test_lock_labels_cannot_read_outside_the_original_module(self):
        for label in ("//:../secret", "//../outside:secret", "//:/etc/passwd", "@other//:secret"):
            with self.subTest(label=label), self.assertRaises(ValueError):
                pip.relative_lock(label)
        receipt = self.prepare()
        outside = self.root / "outside"
        outside.write_text("not a source lock")
        self.lock.unlink()
        self.lock.symlink_to(outside)
        with self.assertRaisesRegex(ValueError, "outside"):
            pip.record_locks(receipt, self.root, self.artifacts, lambda *_: [self.source / "MODULE.bazel"])
