"""Exercise source-set routing and preflight failure before consumer startup."""

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("github_catalog_registry_ci", ROOT / "ci/registry_ci.py")
registry = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(registry)


class SourceCatalogTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.directory = self.root / "ci/github_sources"
        self.directory.mkdir(parents=True)
        self.entry = {"module": "example", "version": "1.0", "execution_architecture": "amd64",
                      "manifests": ["tools.json"]}
        self.catalog = {"schema_version": 1, "inputs": [self.entry]}
        self.manifest = self.directory / "tools.json"
        self.manifest.write_text('{"fixture": true}\n')
        self.write_catalog()

    def write_catalog(self):
        (self.directory / "catalog.json").write_text(json.dumps(self.catalog))

    def test_routes_only_exact_version_and_execution_architecture(self):
        for module, version, execution, expected in (
            ("example", "1.0", "amd64", [self.manifest]),
            ("example", "1.0", "arm64", []),
            ("example", "1.1", "amd64", []),
            ("another", "1.0", "amd64", []),
        ):
            with self.subTest(module=module, version=version, execution=execution):
                self.assertEqual(registry.github_source_manifests(self.root, module, version, execution), expected)

    def test_invalid_and_duplicate_selectors_are_rejected(self):
        for field, invalid in (("module", "../other"), ("version", "1/2"),
                               ("execution_architecture", "x64"), ("manifests", ["../tools.json"]),
                               ("manifests", ["catalog.json"]), ("manifests", ["tools.json", "tools.json"])):
            with self.subTest(field=field, invalid=invalid):
                self.catalog["inputs"] = [{**self.entry, field: invalid}]
                self.write_catalog()
                with self.assertRaises(registry.RegistryError):
                    registry.github_source_manifests(self.root, "example", "1.0", "amd64")
        self.catalog["inputs"] = [self.entry, self.entry]
        self.write_catalog()
        with self.assertRaisesRegex(registry.RegistryError, "Duplicate"):
            registry.github_source_manifests(self.root, "example", "1.0", "amd64")

    def test_missing_or_linked_selected_manifest_fails(self):
        self.manifest.unlink()
        with self.assertRaisesRegex(registry.RegistryError, "missing or linked"):
            registry.github_source_manifests(self.root, "example", "1.0", "amd64")
        self.manifest.symlink_to(self.directory / "catalog.json")
        with self.assertRaisesRegex(registry.RegistryError, "missing or linked"):
            registry.github_source_manifests(self.root, "example", "1.0", "amd64")

    def test_verified_generations_are_separate_and_receipts_retained(self):
        work, artifacts = self.root / "work", self.root / "artifacts"
        with mock.patch.object(registry.github_sources, "prepare", return_value={}) as prepare:
            first = registry.prepare_github_sources(self.root, "example", "1.0", "amd64", work, artifacts)
            self.assertEqual(len(first), 1)
            path = Path(first[0].removeprefix("--distdir="))
            self.assertTrue(path.is_relative_to(work / "github-inputs"))
            self.assertEqual(prepare.call_args.args[:2], (self.manifest, path))
            self.assertTrue(prepare.call_args.args[3].is_relative_to(artifacts / "github-sources"))
            self.manifest.write_text('{"fixture": false}\n')
            second = registry.prepare_github_sources(self.root, "example", "1.0", "amd64", work, artifacts)
            self.assertNotEqual(first, second)

    def test_unverified_source_never_returns_a_distdir_flag(self):
        with mock.patch.object(registry.github_sources, "prepare", side_effect=ValueError("SHA256 mismatch")):
            with self.assertRaisesRegex(registry.RegistryError, "SHA256 mismatch"):
                registry.prepare_github_sources(self.root, "example", "1.0", "amd64",
                                                self.root / "work", self.root / "artifacts")

    def test_committed_cosmos_manifest_selects_both_native_launchers(self):
        selected = registry.github_source_manifests(ROOT, "libteam", "1.31.0.sonic.1", "amd64")
        self.assertEqual([p.name for p in selected], ["cosmos-4.0.2.json"])
        manifest, _ = registry.github_sources.load_manifest(selected[0])
        source = manifest["sources"][0]
        self.assertEqual(source["url"], "https://github.com/jart/cosmopolitan/releases/download/4.0.2/cosmos-4.0.2.zip")
        self.assertNotIn("sha256", source)  # Upstream does not publish a whole-ZIP digest.
        self.assertEqual({f["name"] for f in source["files"]},
                         {"assimilate", "ape-x86_64.elf", "ape-aarch64.elf", "ape-arm64.elf", "gzip.ape"})
        for execution in ("amd64", "arm64"):
            with self.subTest(execution=execution):
                self.assertEqual(registry.github_source_manifests(ROOT, "libteam", "1.31.0.sonic.1", execution), selected)
        self.assertEqual(registry.github_source_manifests(ROOT, "libteam", "1.31.0.sonic.2", "arm64"), [])

    def test_cross_resolution_keeps_distdir_and_private_downloader_together(self):
        flags = ["--distdir=/verified/generation", "--experimental_downloader_config=/private/config",
                 "--platforms=@target//:arm64"]
        self.assertEqual(registry.cross_toolchain.resolution_flags(flags), flags[:2])


if __name__ == "__main__":
    unittest.main()
