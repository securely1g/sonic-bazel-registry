"""Regression tests for registry CI's fail-closed merge checks."""

from __future__ import annotations

import ast
import base64
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import io


SPEC = importlib.util.spec_from_file_location(
    "registry_ci", Path(__file__).resolve().parents[1] / "registry_ci.py"
)
assert SPEC is not None and SPEC.loader is not None
registry_ci = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = registry_ci
SPEC.loader.exec_module(registry_ci)


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


def digest(data: bytes) -> str:
    return "sha256-" + base64.b64encode(hashlib.sha256(data).digest()).decode()


class FixtureTestCase(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def entry(self, module: str, version: str, configured: bool = True) -> Path:
        entry = self.root / "modules" / module / version
        entry.mkdir(parents=True)
        metadata_path = entry.parent / "metadata.json"
        metadata = json.loads(metadata_path.read_text()) if metadata_path.exists() else {"versions": []}
        metadata["versions"].append(version)
        write_json(metadata_path, metadata)
        (entry / "MODULE.bazel").write_text(
            f'module(name = "{module}", version = "{version}")\n'
        )
        write_json(entry / "source.json", {
            "url": "https://example.invalid/source.tar.gz",
            "integrity": digest(b"source archive"),
        })
        if configured:
            write_json(entry / "presubmit.json", {
                "architectures": ["amd64"],
                "consumer_deps": [{"name": "platforms", "version": "1.0.0"}],
                "platforms": {"amd64": "@platforms//host:host"},
                "build_targets": [f"@{module}//:library"],
                "test_targets": [f"@{module}//:consumer_test"],
            })
        return entry

    def git(self, *args: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(self.root), *args], check=True, text=True, capture_output=True,
            env={**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"},
        )
        return result.stdout.strip()

    def commit(self, message: str) -> str:
        if not (self.root / ".git").exists():
            self.git("init", "--quiet")
        self.git("add", "--all")
        self.git(
            "-c", "user.name=Registry CI fixture", "-c", "user.email=fixture@example.invalid",
            "-c", "commit.gpgsign=false", "commit", "--quiet", "-m", message,
        )
        return self.git("rev-parse", "HEAD")

    def selected(self, base: str, head: str) -> set[tuple[str, str]]:
        return {
            (job["module"], job["version"])
            for job in registry_ci.plan(self.root, base, head)["include"]
        }


class SelectionTests(FixtureTestCase):
    def test_changed_version_is_selected_without_unrelated_versions(self) -> None:
        changed = self.entry("alpha", "1.0.0")
        self.entry("alpha", "2.0.0")
        self.entry("beta", "1.0.0")
        base = self.commit("initial registry")
        (changed / "README.md").write_text("Updated module instructions.\n")
        head = self.commit("change alpha version")
        self.assertEqual(self.selected(base, head), {("alpha", "1.0.0")})

    def test_metadata_change_selects_every_existing_version(self) -> None:
        entry = self.entry("alpha", "1.0.0")
        self.entry("alpha", "2.0.0")
        base = self.commit("initial registry")
        metadata_path = entry.parent / "metadata.json"
        metadata = json.loads(metadata_path.read_text())
        metadata["homepage"] = "https://example.invalid/alpha"
        write_json(metadata_path, metadata)
        head = self.commit("change module metadata")
        self.assertEqual(self.selected(base, head), {("alpha", "1.0.0"), ("alpha", "2.0.0")})

    def test_metadata_only_edit_selects_every_existing_version(self) -> None:
        entry = self.entry("alpha", "1.0.0")
        self.entry("alpha", "2.0.0")
        base = self.commit("initial registry")
        metadata_path = entry.parent / "metadata.json"
        metadata_path.write_text(json.dumps(json.loads(metadata_path.read_text()), indent=4) + "\n")
        head = self.commit("reformat module metadata")
        self.assertEqual(self.selected(base, head), {("alpha", "1.0.0"), ("alpha", "2.0.0")})

    def test_new_configured_version_does_not_require_unchanged_legacy_manifest(self) -> None:
        self.entry("alpha", "1.0.0", configured=False)
        base = self.commit("historical unconfigured version")
        self.entry("alpha", "2.0.0")
        head = self.commit("add configured version")
        self.assertEqual(self.selected(base, head), {("alpha", "2.0.0")})

    def test_module_readme_does_not_require_historical_manifests(self) -> None:
        entry = self.entry("alpha", "1.0.0", configured=False)
        base = self.commit("historical unconfigured version")
        (entry.parent / "README.md").write_text("Module release notes.\n")
        head = self.commit("document module")
        self.assertEqual(self.selected(base, head), set())
        self.entry("alpha", "2.0.0")
        head = self.commit("add configured version alongside documentation")
        self.assertEqual(self.selected(base, head), {("alpha", "2.0.0")})

    def test_unknown_module_level_input_is_not_silently_skipped(self) -> None:
        entry = self.entry("alpha", "1.0.0")
        base = self.commit("initial registry")
        (entry.parent / "unexpected.json").write_text("{}\n")
        head = self.commit("add unsupported module input")
        with self.assertRaisesRegex(registry_ci.RegistryError, "Unsupported version path"):
            registry_ci.plan(self.root, base, head)

    def test_changed_version_without_manifest_fails_planning(self) -> None:
        entry = self.entry("alpha", "1.0.0", configured=False)
        base = self.commit("historical unconfigured version")
        (entry / "README.md").write_text("Changed historical version.\n")
        head = self.commit("change unconfigured version")
        with self.assertRaises(registry_ci.RegistryError):
            registry_ci.plan(self.root, base, head)

    def test_deleted_version_fails_planning(self) -> None:
        entry = self.entry("alpha", "1.0.0")
        base = self.commit("initial registry")
        shutil.rmtree(entry)
        write_json(entry.parent / "metadata.json", {"versions": []})
        head = self.commit("delete version")
        with self.assertRaises(registry_ci.RegistryError):
            registry_ci.plan(self.root, base, head)

    def test_renaming_version_cannot_hide_deleted_version(self) -> None:
        entry = self.entry("alpha", "1.0.0")
        base = self.commit("initial registry")
        renamed = entry.with_name("2.0.0")
        entry.rename(renamed)
        (renamed / "MODULE.bazel").write_text('module(name = "alpha", version = "2.0.0")\n')
        write_json(renamed.parent / "metadata.json", {"versions": ["2.0.0"]})
        head = self.commit("rename version")
        with self.assertRaises(registry_ci.RegistryError):
            registry_ci.plan(self.root, base, head)

    def test_infrastructure_changes_select_all_configured_versions(self) -> None:
        self.entry("alpha", "1.0.0")
        self.entry("beta", "2.0.0")
        self.entry("legacy", "1.0.0", configured=False)
        paths = [
            self.root / "ci" / "registry_ci.py",
            self.root / ".github" / "workflows" / "registry.yml",
            self.root / "bazel_registry.json",
        ]
        for path in paths:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("initial\n")
        base = self.commit("initial registry and CI")
        for path in paths:
            with self.subTest(path=path.relative_to(self.root)):
                path.write_text("changed\n")
                head = self.commit(f"change {path.name}")
                self.assertEqual(self.selected(base, head), {("alpha", "1.0.0"), ("beta", "2.0.0")})
                base = head

    def test_all_mode_selects_only_configured_versions(self) -> None:
        self.entry("alpha", "1.0.0")
        self.entry("legacy", "1.0.0", configured=False)
        jobs = registry_ci.plan(self.root, None, None, all_versions=True)["include"]
        self.assertEqual({(job["module"], job["version"]) for job in jobs}, {("alpha", "1.0.0")})

    def test_no_relevant_change_produces_empty_matrix(self) -> None:
        self.entry("alpha", "1.0.0")
        base = self.commit("initial registry")
        (self.root / "README.md").write_text("Registry documentation.\n")
        head = self.commit("document registry")
        self.assertEqual(registry_ci.plan(self.root, base, head), {"include": []})
        self.assertEqual(registry_ci.plan(self.root, head, head), {"include": []})


class EntryValidationTests(FixtureTestCase):
    def test_optional_host_platforms_require_complete_explicit_architecture_map(self) -> None:
        entry = self.entry("alpha", "1.0.0")
        path = entry / "presubmit.json"
        config = json.loads(path.read_text())
        config["architectures"] = ["amd64", "arm64"]
        config["platforms"] = {arch: "@alpha//:target_" + arch for arch in config["architectures"]}
        hosts = {arch: "@alpha//:host_" + arch for arch in config["architectures"]}
        write_json(path, {**config, "host_platforms": hosts})
        self.assertEqual(registry_ci.validate_entry(self.root, "alpha", "1.0.0")["host_platforms"], hosts)
        for invalid in (None, {}, [], {"amd64": hosts["amd64"]},
                        {**hosts, "armhf": "@alpha//:armhf"},
                        {**hosts, "amd64": "//:ambient"},
                        {**hosts, "amd64": "@alpha//:host --override_module=bad"}):
            with self.subTest(host_platforms=invalid):
                write_json(path, {**config, "host_platforms": invalid})
                with self.assertRaisesRegex(registry_ci.RegistryError, "host_platforms must map"):
                    registry_ci.validate_entry(self.root, "alpha", "1.0.0")

    def test_version_overrides_and_dependency_pin_fields_are_rejected(self) -> None:
        entry = self.entry("alpha", "1.0.0")
        path = entry / "presubmit.json"
        config = json.loads(path.read_text())
        for overrides in ({}, {"platforms": "0.9.0"}, {"alpha": "1.0.0"}):
            with self.subTest(overrides=overrides):
                write_json(path, {**config, "version_overrides": overrides})
                with self.assertRaises(registry_ci.RegistryError):
                    registry_ci.validate_entry(self.root, "alpha", "1.0.0")
        for extra in ({"pin": True}, {"pin": False}, {"patches": []}):
            with self.subTest(extra=extra):
                invalid = copy.deepcopy(config)
                invalid["consumer_deps"][0].update(extra)
                write_json(path, invalid)
                with self.assertRaises(registry_ci.RegistryError):
                    registry_ci.validate_entry(self.root, "alpha", "1.0.0")

    def test_valid_entry_is_accepted(self) -> None:
        self.entry("alpha", "1.0.0")
        config = registry_ci.validate_entry(self.root, "alpha", "1.0.0")
        self.assertEqual(config["test_targets"], ["@alpha//:consumer_test"])

    def test_module_feature_settings_are_optional_and_explicit(self) -> None:
        entry = self.entry("alpha", "1.0.0")
        path = entry / "presubmit.json"
        config = json.loads(path.read_text())
        for flags in ([], ["--@alpha//bazel:yang_modules=False"]):
            with self.subTest(flags=flags):
                config["build_flags"] = flags
                write_json(path, config)
                self.assertEqual(registry_ci.validate_entry(self.root, "alpha", "1.0.0")["build_flags"], flags)

    def test_go_sdk_requires_an_explicit_rules_go_dependency(self) -> None:
        entry = self.entry("alpha", "1.0.0")
        path = entry / "presubmit.json"
        config = json.loads(path.read_text())
        config["go_sdk"] = {"version": "1.25.0"}
        write_json(path, config)
        with self.assertRaisesRegex(registry_ci.RegistryError, "requires rules_go"):
            registry_ci.validate_entry(self.root, "alpha", "1.0.0")
        config["consumer_deps"].append({"name": "rules_go", "version": "0.64.1-sonic.1"})
        write_json(path, config)
        self.assertEqual(registry_ci.validate_entry(self.root, "alpha", "1.0.0")["go_sdk"],
                         {"version": "1.25.0"})

    def test_rust_toolchain_requires_an_explicit_rules_rs_dependency(self) -> None:
        entry = self.entry("alpha", "1.0.0")
        path = entry / "presubmit.json"
        config = json.loads(path.read_text())
        config["rust_toolchain"] = {"version": "1.90.0"}
        write_json(path, config)
        with self.assertRaisesRegex(registry_ci.RegistryError, "requires rules_rs"):
            registry_ci.validate_entry(self.root, "alpha", "1.0.0")
        config["consumer_deps"].append({"name": "rules_rs", "version": "0.1.0"})
        write_json(path, config)
        self.assertEqual(registry_ci.validate_entry(self.root, "alpha", "1.0.0")["rust_toolchain"],
                         {"version": "1.90.0"})

    def test_rust_toolchain_rejects_unpinned_versions_and_arbitrary_configuration(self) -> None:
        entry = self.entry("rules_rs", "0.1.0")
        path = entry / "presubmit.json"
        config = json.loads(path.read_text())
        cases = [None, "1.90.0", {}, {"version": 1900}, {"version": "latest"},
                 {"version": "nightly"}, {"version": "1.90"}, {"version": "1.90.0-beta"},
                 {"version": "1.90.0\n"}, {"version": '1.90.0")'},
                 {"version": "1.90.0", "url": "https://example.invalid"},
                 {"version": "1.90.0", "bindgen": "true"},
                 {"version": "1.90.0", "mangled_allocator_libraries": 1}]
        for toolchain in cases:
            with self.subTest(toolchain=toolchain):
                write_json(path, {**config, "rust_toolchain": toolchain})
                with self.assertRaises(registry_ci.RegistryError):
                    registry_ci.validate_entry(self.root, "rules_rs", "0.1.0")

    def test_go_sdk_rejects_unpinned_versions_and_arbitrary_configuration(self) -> None:
        entry = self.entry("rules_go", "0.64.1-sonic.1")
        path = entry / "presubmit.json"
        config = json.loads(path.read_text())
        cases = [None, "1.25.0", {}, {"version": 1250}, {"version": "latest"},
                 {"version": "1.25"}, {"version": "1.25.0rc1"},
                 {"version": "1.25.0\n"}, {"version": '1.25.0")'},
                 {"version": "1.25.0", "url": "https://example.invalid"}]
        for sdk in cases:
            with self.subTest(sdk=sdk):
                write_json(path, {**config, "go_sdk": sdk})
                with self.assertRaises(registry_ci.RegistryError):
                    registry_ci.validate_entry(self.root, "rules_go", "0.64.1-sonic.1")
        write_json(path, {**config, "go_sdk": {"version": "1.25.0"}})
        self.assertEqual(registry_ci.validate_entry(self.root, "rules_go", "0.64.1-sonic.1")["go_sdk"],
                         {"version": "1.25.0"})

    def test_build_flags_cannot_redirect_or_disable_validation(self) -> None:
        entry = self.entry("alpha", "1.0.0")
        path = entry / "presubmit.json"
        config = json.loads(path.read_text())
        cases = (
            "--@alpha//:feature=False", [1], ["--registry=https://example.invalid"],
            ["--cache_test_results"], ["--test_tag_filters=-all"],
            ["--@beta//:feature=False"], ["--@alpha//:feature"],
            ["--@alpha//:feature="], ["--@alpha//:feature=False --cache_test_results"],
            ["--@alpha//:feature=False", "--@alpha//:feature=True"],
        )
        for flags in cases:
            with self.subTest(flags=flags):
                config["build_flags"] = flags
                write_json(path, config)
                with self.assertRaises(registry_ci.RegistryError):
                    registry_ci.validate_entry(self.root, "alpha", "1.0.0")

    def test_malformed_source_integrity_is_rejected(self) -> None:
        entry = self.entry("alpha", "1.0.0")
        source_path = entry / "source.json"
        source = json.loads(source_path.read_text())
        for integrity in ("sha256-not-base64!", "sha256-YQ==", digest(b"archive").replace("sha256", "md5")):
            with self.subTest(integrity=integrity):
                source["integrity"] = integrity
                write_json(source_path, source)
                with self.assertRaises(registry_ci.RegistryError):
                    registry_ci.validate_entry(self.root, "alpha", "1.0.0")

    def test_corrupted_patch_and_overlay_are_rejected(self) -> None:
        entry = self.entry("alpha", "1.0.0")
        source_path = entry / "source.json"
        source = json.loads(source_path.read_text())
        for field, folder, name in (("patches", "patches", "fix.patch"), ("overlay", "overlay", "BUILD.bazel")):
            with self.subTest(field=field):
                path = entry / folder / name
                path.parent.mkdir(parents=True, exist_ok=True)
                expected = b"expected registry input\n"
                path.write_bytes(expected)
                source[field] = {name: digest(expected)}
                write_json(source_path, source)
                path.write_bytes(b"changed without updating integrity\n")
                with self.assertRaises(registry_ci.RegistryError):
                    registry_ci.validate_entry(self.root, "alpha", "1.0.0")
                path.write_bytes(expected)

    def test_registry_module_identity_must_match_directory(self) -> None:
        entry = self.entry("alpha", "1.0.0")
        for name, version in (("beta", "1.0.0"), ("alpha", "2.0.0")):
            with self.subTest(name=name, version=version):
                (entry / "MODULE.bazel").write_text(f'module(name = "{name}", version = "{version}")\n')
                with self.assertRaises(registry_ci.RegistryError):
                    registry_ci.validate_entry(self.root, "alpha", "1.0.0")

    def test_metadata_must_list_the_version(self) -> None:
        entry = self.entry("alpha", "1.0.0")
        write_json(entry.parent / "metadata.json", {"versions": ["2.0.0"]})
        with self.assertRaises(registry_ci.RegistryError):
            registry_ci.validate_entry(self.root, "alpha", "1.0.0")

    def test_module_identity_requires_literals_and_ignores_comments(self) -> None:
        text = '# module(name = "wrong", version = "0")\nmodule(\n    name = "alpha",\n    version = "1.0.0",\n)\n'
        self.assertEqual(registry_ci.parse_module_identity(text), ("alpha", "1.0.0"))
        with self.assertRaises(registry_ci.RegistryError):
            registry_ci.parse_module_identity('NAME = "alpha"\nmodule(name = NAME, version = "1.0.0")\n')

    def test_module_identity_ignores_extension_module_methods(self) -> None:
        # rules_go 0.64.1 uses go_deps.module() for its tool dependencies.
        text = '''module(
    name = "rules_go",
    version = "0.64.1",
)
dev_go_deps = use_extension("@gazelle//:extensions.bzl", "go_deps", dev_dependency = True)
dev_go_deps.module(
    path = "github.com/bazelbuild/buildtools",
    version = "v0.0.0-20231103205921-433ea8554e82",
)
other_extension.module(name = "unrelated", version = "2.0.0")
'''
        self.assertEqual(registry_ci.parse_module_identity(text), ("rules_go", "0.64.1"))

    def test_module_methods_do_not_replace_or_hide_duplicate_declarations(self) -> None:
        method = 'extension.module(name = "alpha", version = "1.0.0")\n'
        declaration = 'module(name = "alpha", version = "1.0.0")\n'
        for declarations in ("", declaration * 2):
            with self.subTest(declarations=declarations):
                with self.assertRaisesRegex(registry_ci.RegistryError, "exactly one module\\(\\) declaration"):
                    registry_ci.parse_module_identity(method + declarations + method)


class GeneratedModuleOverlayTests(FixtureTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.directory = self.entry("alpha", "1.0.0")
        self.canonical = self.directory / "MODULE.bazel"
        self.overlay = self.directory / "overlay/MODULE.bazel"
        self.source = self.directory / "source.json"
        self.presubmit = self.directory / "presubmit.json"
        self.config = json.loads(self.presubmit.read_text())
        write_json(self.presubmit, {**self.config, "generated_module_overlay": True})

    def sync(self, check: bool = False) -> None:
        registry_ci.sync_module(self.root, "alpha", "1.0.0", check)

    def files(self) -> dict:
        return {path.relative_to(self.root): (path.read_bytes(), path.stat().st_mtime_ns)
                for path in self.root.rglob("*") if path.is_file()}

    def test_generates_missing_overlay_preserving_canonical_and_other_source_fields(self) -> None:
        before = self.canonical.read_bytes()
        source = json.loads(self.source.read_text())
        source["strip_prefix"] = "upstream-1.0.0"
        other = self.directory / "overlay/BUILD.bazel"
        other.parent.mkdir()
        other.write_bytes(b"# separately maintained BUILD\n")
        source["overlay"] = {"BUILD.bazel": digest(other.read_bytes())}
        write_json(self.source, source)
        self.sync()
        self.assertEqual(self.canonical.read_bytes(), before)
        generated = self.overlay.read_bytes()
        self.assertTrue(generated.startswith(b"# AUTO-GENERATED. DO NOT EDIT MANUALLY.\n"))
        self.assertIn(b"# Source: ../MODULE.bazel\n", generated)
        self.assertIn(b"sync-module --module alpha --version 1.0.0", generated)
        self.assertEqual(generated.split(b"\n\n", 1)[1], before)
        source["overlay"]["MODULE.bazel"] = digest(generated)
        self.assertEqual(json.loads(self.source.read_text()), source)
        registry_ci.validate_entry(self.root, "alpha", "1.0.0")

    def test_check_mode_and_repeated_generation_do_not_write(self) -> None:
        before = self.files()
        with self.assertRaisesRegex(registry_ci.RegistryError, "run: .*sync-module"):
            self.sync(check=True)
        self.assertEqual(self.files(), before)
        self.assertFalse(self.overlay.parent.exists())
        self.sync()
        before = self.files()
        self.sync(check=True)
        self.sync()
        self.assertEqual(self.files(), before)

    def test_canonical_dependency_change_requires_generation_before_validation(self) -> None:
        self.sync()
        self.canonical.write_bytes(self.canonical.read_bytes() + b'bazel_dep(name = "beta", version = "2.0.0")\n')
        before = self.files()
        with self.assertRaisesRegex(registry_ci.RegistryError, "differs from canonical"):
            self.sync(check=True)
        with self.assertRaisesRegex(registry_ci.RegistryError, "differs from canonical"):
            registry_ci.validate_entry(self.root, "alpha", "1.0.0")
        self.assertEqual(self.files(), before)
        self.sync()
        self.sync(check=True)
        self.assertTrue(self.overlay.read_bytes().endswith(self.canonical.read_bytes()))

    def test_direct_overlay_edit_is_rejected_even_with_refreshed_checksum(self) -> None:
        self.sync()
        self.overlay.write_bytes(self.overlay.read_bytes() + b'bazel_dep(name = "unreviewed", version = "9.0.0")\n')
        source = json.loads(self.source.read_text())
        source["overlay"]["MODULE.bazel"] = digest(self.overlay.read_bytes())
        write_json(self.source, source)
        with self.assertRaisesRegex(registry_ci.RegistryError, "differs from canonical"):
            registry_ci.validate_entry(self.root, "alpha", "1.0.0")
        self.sync()
        self.sync(check=True)

    def test_corrupted_checksum_is_detected_and_repaired_without_rewriting_overlay(self) -> None:
        self.sync()
        source = json.loads(self.source.read_text())
        source["overlay"]["MODULE.bazel"] = digest(b"wrong")
        write_json(self.source, source)
        before = self.files()
        with self.assertRaisesRegex(registry_ci.RegistryError, "Integrity checksum mismatch; run:"):
            self.sync(check=True)
        self.assertEqual(self.files(), before)
        self.sync()
        self.assertEqual(self.files()[self.overlay.relative_to(self.root)], before[self.overlay.relative_to(self.root)])
        self.sync(check=True)

    def test_opt_in_is_literal_true_and_legacy_entries_keep_independent_overlays(self) -> None:
        for value in (False, None, 1, "true"):
            with self.subTest(value=value):
                write_json(self.presubmit, {**self.config, "generated_module_overlay": value})
                with self.assertRaisesRegex(registry_ci.RegistryError, "must be true"):
                    registry_ci.validate_entry(self.root, "alpha", "1.0.0")
                with self.assertRaisesRegex(registry_ci.RegistryError, "requires generated_module_overlay"):
                    self.sync()
        write_json(self.presubmit, self.config)
        self.overlay.parent.mkdir()
        self.overlay.write_bytes(self.canonical.read_bytes() + b"# independently maintained legacy overlay\n")
        source = json.loads(self.source.read_text())
        source["overlay"] = {"MODULE.bazel": digest(self.overlay.read_bytes())}
        write_json(self.source, source)
        before = self.files()
        self.assertEqual(registry_ci.validate_entry(self.root, "alpha", "1.0.0"), self.config)
        with self.assertRaises(registry_ci.RegistryError):
            self.sync()
        self.assertEqual(self.files(), before)

    def test_generation_rejects_output_aliases_and_wrong_canonical_identity(self) -> None:
        self.canonical.write_text('module(name = "other", version = "1.0.0")\n')
        before = self.files()
        with self.assertRaisesRegex(registry_ci.RegistryError, "identity"):
            self.sync()
        self.assertEqual(self.files(), before)
        self.canonical.write_text('module(name = "alpha", version = "1.0.0")\n')
        outside = self.root / "outside"
        outside.mkdir()
        self.overlay.parent.symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(registry_ci.RegistryError, "real directory"):
            self.sync()
        self.assertEqual(list(outside.iterdir()), [])
        self.overlay.parent.unlink()
        self.overlay.parent.mkdir()
        self.overlay.symlink_to(self.canonical)
        with self.assertRaisesRegex(registry_ci.RegistryError, "symlink"):
            self.sync()
        self.overlay.unlink()
        self.overlay.hardlink_to(self.canonical)
        before = self.files()
        with self.assertRaisesRegex(registry_ci.RegistryError, "hard-linked"):
            self.sync()
        self.assertEqual(self.files(), before)

    def test_cli_supports_generation_and_read_only_check(self) -> None:
        command = ["registry_ci.py", "sync-module", "--module", "alpha", "--version", "1.0.0"]
        with mock.patch.object(registry_ci, "ROOT", self.root), mock.patch.object(sys, "argv", command):
            registry_ci.main()
        before = self.files()
        with mock.patch.object(registry_ci, "ROOT", self.root), mock.patch.object(sys, "argv", command + ["--check"]):
            registry_ci.main()
        self.assertEqual(self.files(), before)


class RustPreparationTests(FixtureTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.source = b"# pinned preparation helper\n"
        self.preparation = {
            "module": "alpha", "repo_name": "alpha",
            "helper_revision": "a" * 40,
            "helper_sha256": hashlib.sha256(self.source).hexdigest(),
        }
        self.entry_path = self.entry("alpha", "1.0.0")
        self.config_path = self.entry_path / "presubmit.json"
        self.config = json.loads(self.config_path.read_text())
        self.config["rust_preparation"] = self.preparation
        write_json(self.config_path, self.config)

    def test_preparation_cannot_select_an_undeclared_module_or_mutable_helper(self) -> None:
        self.assertEqual(registry_ci.validate_entry(self.root, "alpha", "1.0.0"), self.config)
        for field, value in (("module", "unrequested"), ("repo_name", "other_alias"),
                             ("helper_revision", "main"), ("helper_sha256", "bad")):
            with self.subTest(field=field):
                config = copy.deepcopy(self.config)
                config["rust_preparation"][field] = value
                write_json(self.config_path, config)
                with self.assertRaises(registry_ci.RegistryError):
                    registry_ci.validate_entry(self.root, "alpha", "1.0.0")

    def prepare(self, contents: str | None = None, expected_error: str | None = None):
        work = self.root / "work"
        consumer = work / "consumer"
        artifacts = self.root / "artifacts"
        consumer.mkdir(parents=True, exist_ok=True)
        artifacts.mkdir(exist_ok=True)

        def run(command, cwd, log):
            self.assertIn("--shared-only", command)
            self.assertIn("--bazel-arg=--registry=file:///registry", command)
            self.assertNotIn("--bazel-arg=--platforms=@alpha//:platform", command)
            self.assertNotIn("--bazel-arg=--@alpha//:feature=True", command)
            staged = work / "rust-deps" / "alpha-private"
            staged.mkdir(parents=True)
            for name in ("Cargo.toml", "Cargo.lock", "Cargo.Bazel.lock", "preparation.json", "source-resolution.json"):
                (staged / name).write_text(name)
            (work / "rust-overrides.bazelrc").write_text(
                contents if contents is not None else f"common --override_module=alpha={staged}\n")

        with mock.patch.object(registry_ci, "urlopen", return_value=io.BytesIO(self.source)), \
                mock.patch.object(registry_ci, "run_logged", side_effect=run) as execute:
            if expected_error is not None:
                with self.assertRaisesRegex(registry_ci.RegistryError, expected_error):
                    registry_ci.prepare_rust(self.config, consumer, work, artifacts, "bazel", [])
                execute.assert_not_called()
                return
            flags = registry_ci.prepare_rust(self.config, consumer, work, artifacts, "bazel", [
                "--registry=file:///registry", "--platforms=@alpha//:platform", "--@alpha//:feature=True",
            ])
        return flags, execute, artifacts

    def test_helper_checksum_is_verified_before_execution(self) -> None:
        self.preparation["helper_sha256"] = "0" * 64
        self.prepare(expected_error="checksum mismatch")

    def test_shared_lock_and_resolution_evidence_are_retained(self) -> None:
        flags, execute, artifacts = self.prepare()
        self.assertEqual(flags, [f"--override_module=alpha={self.root / 'work/rust-deps/alpha-private'}"])
        execute.assert_called_once()
        self.assertEqual((artifacts / "shared-rust-Cargo.lock").read_text(), "Cargo.lock")
        self.assertEqual((artifacts / "shared-rust-source-resolution.json").read_text(), "source-resolution.json")

    def test_helper_cannot_change_other_modules_or_runner_options(self) -> None:
        with self.assertRaisesRegex(registry_ci.RegistryError, "exactly its declared module"):
            self.prepare("common --override_module=other=/tmp/other\ncommon --remote_cache=https://invalid\n")

    def test_helper_cannot_redirect_outside_private_staging(self) -> None:
        with self.assertRaisesRegex(registry_ci.RegistryError, "private staging"):
            self.prepare("common --override_module=alpha=/tmp/other\n")


class RequiredTestResultTests(FixtureTestCase):
    label = "@alpha//:consumer_test"

    def events(self) -> list[dict]:
        canonical = "@@alpha+//:consumer_test"
        return [
            {"id": {"testResult": {"label": canonical, "run": 1, "shard": 0, "attempt": 1}},
             "testResult": {"status": "PASSED", "cachedLocally": False,
                            "executionInfo": {"cachedRemotely": False}}},
            {"id": {"testSummary": {"label": canonical}},
             "testSummary": {"overallStatus": "PASSED", "totalRunCount": 1, "totalNumCached": 0}},
        ]

    def verify(self, events: list[dict], labels: list[str] | None = None) -> None:
        path = self.root / "test-events.jsonl"
        path.write_text("".join(json.dumps(event) + "\n" for event in events))
        registry_ci.verify_tests(path, labels or [self.label])

    def test_uncached_canonical_test_result_is_accepted(self) -> None:
        self.verify(self.events())

    def test_every_required_test_needs_a_result_and_summary(self) -> None:
        events = self.events()
        for incomplete in ([], events[:1], events[1:]):
            with self.subTest(events=incomplete):
                with self.assertRaises(registry_ci.RegistryError):
                    self.verify(incomplete)
        with self.assertRaises(registry_ci.RegistryError):
            self.verify(events, [self.label, "@alpha//:package_test"])

    def test_incompatible_or_skipped_required_target_is_rejected(self) -> None:
        events = [{"id": {"targetCompleted": {"label": "@@alpha+//:consumer_test"}},
                   "aborted": {"reason": "SKIPPED"}}]
        with self.assertRaises(registry_ci.RegistryError):
            self.verify(events)

    def test_cached_or_zero_run_results_are_rejected(self) -> None:
        cases = (
            (0, ("testResult", "cachedLocally"), True),
            (0, ("testResult", "executionInfo", "cachedRemotely"), True),
            (1, ("testSummary", "totalNumCached"), 1),
            (1, ("testSummary", "totalRunCount"), 0),
        )
        for event_index, keys, value in cases:
            with self.subTest(field=".".join(keys)):
                events = copy.deepcopy(self.events())
                target = events[event_index]
                for key in keys[:-1]:
                    target = target[key]
                target[keys[-1]] = value
                with self.assertRaises(registry_ci.RegistryError):
                    self.verify(events)

    def test_failed_attempt_is_rejected_even_with_passed_summary(self) -> None:
        events = self.events()
        events[0]["testResult"]["status"] = "FAILED"
        with self.assertRaises(registry_ci.RegistryError):
            self.verify(events)


class BuildOutputTests(FixtureTestCase):
    labels = ["@alpha//:runtime", "@alpha//:debug"]

    def events(self) -> list[dict]:
        self.work = self.root / "work"
        self.work.mkdir(exist_ok=True)
        events = []
        for name in ("runtime", "debug"):
            output = self.work / f"{name}.tar"
            output.write_bytes(name.encode())
            events.extend([
                {"id": {"namedSet": {"id": name}}, "namedSetOfFiles": {"files": [
                    {"name": output.name, "pathPrefix": ["bazel-out", "bin"], "uri": output.as_uri()},
                ]}},
                {"id": {"targetCompleted": {"label": f"@@alpha+//:{name}"}},
                 "completed": {"success": True, "outputGroup": [
                     {"name": "default", "fileSets": [{"id": name}]},
                     {"name": "unused_group", "fileSets": [{"id": "not-needed"}]},
                 ]}},
            ])
        return events

    def collect(self, events: list[dict]) -> dict:
        bep = self.root / "build-events.jsonl"
        bep.write_text("".join(json.dumps(event) + "\n" for event in events))
        artifacts = self.root / "artifacts"
        registry_ci.collect_outputs(bep, self.labels, self.work, artifacts)
        return json.loads((artifacts / "outputs.json").read_text())

    def test_runtime_debug_pair_and_hashes_are_retained(self) -> None:
        index = self.collect(self.events())
        self.assertEqual(set(index), set(self.labels))
        for label, files in index.items():
            self.assertEqual(len(files), 1)
            data = (self.root / "artifacts" / files[0]["path"]).read_bytes()
            self.assertEqual(data, label.rsplit(":", 1)[1].encode())
            self.assertEqual(files[0]["sha256"], hashlib.sha256(data).hexdigest())
            self.assertEqual(files[0]["size"], len(data))

    def test_nested_sets_tree_outputs_and_repeated_files(self) -> None:
        events = self.events()
        tree = self.work / "models"
        tree.mkdir()
        (tree / "model.yang").write_text("module fixture {}")
        events[0]["namedSetOfFiles"] = {"fileSets": [{"id": "nested"}, {"id": "nested"}]}
        events.append({"id": {"namedSet": {"id": "nested"}}, "namedSetOfFiles": {"files": [
            {"name": "models", "uri": tree.as_uri()},
        ]}})
        index = self.collect(events)
        self.assertEqual(len(index[self.labels[0]]), 1)
        self.assertEqual(index[self.labels[0]][0]["path"], "outputs/models/model.yang")

    def test_missing_required_target_or_output_is_rejected(self) -> None:
        events = self.events()
        with self.assertRaisesRegex(registry_ci.RegistryError, "did not complete"):
            self.collect(events[:2])
        shutil.rmtree(self.root / "artifacts")
        (self.work / "debug.tar").unlink()
        with self.assertRaisesRegex(registry_ci.RegistryError, "Missing regular"):
            self.collect(events)

    def test_unsafe_paths_and_outside_symlink_are_rejected(self) -> None:
        for kind in ("parent", "absolute", "outside", "cycle"):
            with self.subTest(kind=kind):
                events = self.events()
                output = events[0]["namedSetOfFiles"]["files"][0]
                if kind in ("parent", "absolute"):
                    output["name"] = "../outside" if kind == "parent" else "/outside"
                    output["pathPrefix"] = []
                elif kind == "outside":
                    (self.root / "secret").write_text("not a build output")
                    (self.work / "link").symlink_to(self.root / "secret")
                    output["uri"] = (self.work / "link").as_uri()
                else:
                    events[0]["namedSetOfFiles"] = {"fileSets": [{"id": "runtime"}]}
                with self.assertRaises(registry_ci.RegistryError):
                    self.collect(events)
                shutil.rmtree(self.root / "artifacts")

    def test_conflicting_output_destinations_are_rejected(self) -> None:
        events = self.events()
        events[2]["namedSetOfFiles"]["files"][0]["name"] = "runtime.tar"
        with self.assertRaisesRegex(registry_ci.RegistryError, "Conflicting"):
            self.collect(events)


class FailedActionLogTests(FixtureTestCase):
    def collect(self, outputs: list[dict]) -> tuple[Path, list[dict]]:
        self.work = self.root / "work"
        self.work.mkdir(exist_ok=True)
        artifacts = self.root / "artifacts"
        artifacts.mkdir(exist_ok=True)
        bep = artifacts / "build-events.jsonl"
        events = [{"action": {"label": "@@alpha+//:library", "type": "CcCmakeMakeRule",
                              "exitCode": 1, **output}} for output in outputs]
        bep.write_text("".join(json.dumps(event) + "\n" for event in events))
        registry_ci.collect_failed_action_logs(bep, self.work, artifacts)
        index = artifacts / "failed-actions/build-events/index.json"
        return artifacts, json.loads(index.read_text()) if index.exists() else []

    def test_retains_complete_stdout_and_stderr_above_bazel_ui_limit(self) -> None:
        work = self.root / "work"
        work.mkdir()
        stdout, stderr = work / "stdout with spaces", work / "stderr"
        stdout.write_bytes(b"x" * (1024 * 1024 + 100) + b"\ncompiler failure\n")
        stderr.write_bytes(b"error\n")
        artifacts, records = self.collect([{
            "stdout": {"uri": stdout.as_uri(), "name": "../../untrusted-name"},
            "stderr": {"uri": stderr.as_uri()},
        }])
        self.assertEqual(len(records), 2)
        for record, source in zip(records, (stdout, stderr)):
            self.assertEqual((artifacts / record["path"]).read_bytes(), source.read_bytes())
            self.assertEqual(record["size"], source.stat().st_size)
            self.assertEqual(record["sha256"], hashlib.sha256(source.read_bytes()).hexdigest())
            self.assertEqual(record["label"], "@@alpha+//:library")

    def test_unsafe_missing_and_nonregular_logs_are_reported_without_copying(self) -> None:
        work = self.root / "work"
        work.mkdir()
        outside = self.root / "outside"
        outside.write_text("must not copy")
        (work / "escape").symlink_to(outside)
        uris = [outside.as_uri(), (work / "escape").as_uri(),
                (work / "missing").as_uri(), work.as_uri(),
                "https://example.invalid/log", "file://remote.example/log",
                "file:relative", (work / "valid").as_uri() + "?query=1",
                (work / "valid").as_uri() + "#fragment"]
        artifacts, records = self.collect([{"stdout": {"uri": uri}} for uri in uris])
        self.assertEqual(len(records), len(uris))
        self.assertTrue(all("error" in record and "path" not in record for record in records))
        self.assertEqual(list((artifacts / "failed-actions").rglob("*.log")), [])

    def test_successful_actions_and_absent_bep_need_no_failed_logs(self) -> None:
        artifacts, records = self.collect([{"exitCode": 0, "success": True,
                                            "stdout": {"uri": "file:///not-copied"}}])
        self.assertEqual(records, [])
        registry_ci.collect_failed_action_logs(artifacts / "absent.jsonl", self.work, artifacts)
        self.assertFalse((artifacts / "failed-actions").exists())


class FetchedModuleTests(FixtureTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.registry_entry = self.entry("alpha", "1.0.0")
        self.config_path = self.registry_entry / "presubmit.json"
        self.config = json.loads(self.config_path.read_text())
        self.config["build_flags"] = ["--@alpha//bazel:yang_modules=False"]
        self.config["consumer_deps"] = [
            {"name": "platforms", "version": "1.0.0"},
            {"name": "sonic-build-infra", "version": "0.0.7-abc123", "repo_name": "sonic_build_infra"},
        ]
        write_json(self.config_path, self.config)
        self.output_base = self.root / "fake-output-base"
        self.fetched = self.fetched_module("alpha")
        self.fetched.parent.mkdir(parents=True)
        self.fetched.write_bytes((self.registry_entry / "MODULE.bazel").read_bytes())
        for dependency in self.config["consumer_deps"]:
            path = self.fetched_module(dependency["name"])
            path.parent.mkdir(parents=True)
            path.write_text(
                f'module(name = "{dependency["name"]}", version = "{dependency["version"]}")\n'
            )
        self.fake_bazel = self.root / "fake-bazel"
        self.fake_bazel.write_text(
            "#!/usr/bin/env python3\n"
            "import json\n"
            "from pathlib import Path\n"
            "import sys\n"
            "args = sys.argv[1:]\n"
            "assert '--@alpha//bazel:yang_modules=False' in args\n"
            "if 'info' in args:\n"
            f"    print({str(self.output_base)!r})\n"
            "elif 'build' in args:\n"
            "    assert '--lockfile_mode=update' in args\n"
            "    Path('MODULE.bazel.lock').write_text('{\"lockFileVersion\": 13}\\n')\n"
            "    path = next(arg.split('=', 1)[1] for arg in args if arg.startswith('--build_event_json_file='))\n"
            "    output = Path.cwd() / 'library.tar'\n"
            "    output.write_bytes(b'package')\n"
            "    events = [\n"
            "        {'id': {'namedSet': {'id': '0'}}, 'namedSetOfFiles': {'files': [\n"
            "            {'name': 'library.tar', 'uri': output.as_uri()}]}},\n"
            "        {'id': {'targetCompleted': {'label': '@@alpha+//:library'}},\n"
            "         'completed': {'success': True, 'outputGroup': [{'name': 'default', 'fileSets': [{'id': '0'}]}]}},\n"
            "    ]\n"
            "    Path(path).write_text(''.join(json.dumps(event) + '\\n' for event in events))\n"
            "elif 'test' in args:\n"
            "    path = next(arg.split('=', 1)[1] for arg in args if arg.startswith('--build_event_json_file='))\n"
            "    events = [\n"
            "        {'id': {'testResult': {'label': '@@alpha+//:consumer_test'}},\n"
            "         'testResult': {'status': 'PASSED', 'cachedLocally': False}},\n"
            "        {'id': {'testSummary': {'label': '@@alpha+//:consumer_test'}},\n"
            "         'testSummary': {'overallStatus': 'PASSED', 'totalRunCount': 1, 'totalNumCached': 0}},\n"
            "    ]\n"
            "    Path(path).write_text(''.join(json.dumps(event) + '\\n' for event in events))\n"
        )
        self.fake_bazel.chmod(0o755)

    def fetched_module(self, name: str) -> Path:
        return self.output_base / "external" / f"{name}+" / "MODULE.bazel"

    def run_fixture(self, suffix: str, architecture: str = "amd64") -> Path:
        artifacts = self.root / f"artifacts-{suffix}"
        registry_ci.run(
            self.root, "alpha", "1.0.0", architecture,
            self.root / f"work-{suffix}", artifacts, str(self.fake_bazel),
        )
        return artifacts

    def declarations(self, artifacts: Path, function: str) -> list[dict]:
        # The runner generates a literal-only, Python-compatible Starlark subset.
        tree = ast.parse((artifacts / "consumer.MODULE.bazel").read_text())
        return [
            {keyword.arg: ast.literal_eval(keyword.value) for keyword in node.value.keywords}
            for node in tree.body
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Name) and node.value.func.id == function
        ]

    def test_explicit_native_host_platform_reaches_every_bazel_command(self) -> None:
        self.config["architectures"] = ["amd64", "arm64"]
        self.config["platforms"] = {arch: "@alpha//:target_" + arch for arch in self.config["architectures"]}
        self.config["host_platforms"] = {arch: "@alpha//:host_" + arch for arch in self.config["architectures"]}
        write_json(self.config_path, self.config)
        script = self.fake_bazel.read_text()
        for architecture, machine in (("amd64", "x86_64"), ("arm64", "aarch64")):
            with self.subTest(architecture=architecture):
                expected = "--host_platform=" + self.config["host_platforms"][architecture]
                # The fake executable is invoked for build, test and info, so
                # omitting the flag from any actual command fails this fixture.
                self.fake_bazel.write_text(script.replace("args = sys.argv[1:]\n",
                    "args = sys.argv[1:]\n" + f"assert {expected!r} in args\n"))
                with mock.patch.object(registry_ci.platform, "machine", return_value=machine):
                    artifacts = self.run_fixture("host-" + architecture, architecture)
                validation = json.loads((artifacts / "validation.json").read_text())
                self.assertEqual(validation["host_platform"], self.config["host_platforms"][architecture])
                self.assertEqual(validation["platform"], self.config["platforms"][architecture])

    def test_omitted_host_platform_preserves_bazel_default(self) -> None:
        self.fake_bazel.write_text(self.fake_bazel.read_text().replace("args = sys.argv[1:]\n",
            "args = sys.argv[1:]\nassert not any(arg.startswith('--host_platform=') for arg in args)\n"))
        artifacts = self.run_fixture("default-host")
        self.assertIsNone(json.loads((artifacts / "validation.json").read_text())["host_platform"])

    def test_every_consumer_dependency_is_pinned_by_module_name_and_recorded(self) -> None:
        artifacts = self.run_fixture("control")
        self.assertEqual(self.declarations(artifacts, "bazel_dep"), [
            {"name": "alpha", "version": "1.0.0"}, *self.config["consumer_deps"],
        ])
        self.assertEqual(self.declarations(artifacts, "single_version_override"), [
            {"module_name": dependency["name"], "version": dependency["version"]}
            for dependency in self.config["consumer_deps"]
        ])
        validation = json.loads((artifacts / "validation.json").read_text())
        self.assertEqual(validation["build_flags"], self.config["build_flags"])
        self.assertEqual(validation["consumer_deps"], self.config["consumer_deps"])
        self.assertNotIn("version_overrides", validation)
        self.assertTrue(validation["fetched_module_matches_registry"])
        self.assertEqual(json.loads((artifacts / "MODULE.bazel.lock").read_text()), {"lockFileVersion": 13})
        self.assertEqual((self.root / "work-control" / "consumer" / ".gitignore").read_text(), "MODULE.bazel.lock\n")
        self.assertEqual((artifacts / "fetched.MODULE.bazel").read_bytes(), self.fetched.read_bytes())
        for dependency in self.config["consumer_deps"]:
            name = dependency["name"]
            self.assertEqual((artifacts / f"consumer-dep-{name}.MODULE.bazel").read_bytes(),
                             self.fetched_module(name).read_bytes())
        self.assertFalse((artifacts / "consumer-dep-sonic_build_infra.MODULE.bazel").exists())
        outputs = json.loads((artifacts / "outputs.json").read_text())
        self.assertEqual(set(outputs), {"@alpha//:library"})
        self.assertEqual((artifacts / outputs["@alpha//:library"][0]["path"]).read_bytes(), b"package")

    def test_generated_overlay_and_bazel_materialized_canonical_module_are_checked_separately(self) -> None:
        self.config["generated_module_overlay"] = True
        write_json(self.config_path, self.config)
        registry_ci.sync_module(self.root, "alpha", "1.0.0")
        entry = self.config_path.parent
        canonical = (entry / "MODULE.bazel").read_bytes()
        generated = (entry / "overlay/MODULE.bazel").read_bytes()
        # Bazel writes the canonical registry MODULE after overlays/patches.
        self.fetched.write_bytes(canonical)
        artifacts = self.run_fixture("generated-overlay")
        validation = json.loads((artifacts / "validation.json").read_text())
        self.assertTrue(validation["generated_module_overlay"])
        self.assertTrue(validation["fetched_module_matches_registry"])
        self.assertEqual(validation["registry_module_sha256"], hashlib.sha256(canonical).hexdigest())
        self.assertEqual(validation["fetched_module_sha256"], hashlib.sha256(canonical).hexdigest())
        self.assertEqual(validation["generated_module_overlay_sha256"], hashlib.sha256(generated).hexdigest())
        self.fetched.write_bytes(generated)  # Do not weaken the canonical comparison to accept either form.
        with self.assertRaisesRegex(registry_ci.RegistryError, "Fetched MODULE.bazel differs"):
            self.run_fixture("noncanonical-fetched-module")
        (entry / "MODULE.bazel").write_bytes(canonical + b'bazel_dep(name = "new", version = "1.0.0")\n')
        with mock.patch.object(registry_ci, "run_logged") as execute:
            with self.assertRaisesRegex(registry_ci.RegistryError, "differs from canonical"):
                self.run_fixture("stale-generated-overlay")
            execute.assert_not_called()

    def test_go_sdk_uses_the_declared_apparent_repository_and_retains_selection(self) -> None:
        for alias in (None, "io_bazel_rules_go"):
            with self.subTest(alias=alias):
                dependency = {"name": "rules_go", "version": "0.64.1-sonic.1"}
                if alias:
                    dependency["repo_name"] = alias
                self.config["consumer_deps"] = [dependency]
                self.config["go_sdk"] = {"version": "1.25.0"}
                write_json(self.config_path, self.config)
                fetched = self.fetched_module("rules_go")
                fetched.parent.mkdir(exist_ok=True)
                fetched.write_text('module(name = "rules_go", version = "0.64.1-sonic.1")\n')
                artifacts = self.run_fixture(alias or "default-go-alias")
                tree = ast.parse((artifacts / "consumer.MODULE.bazel").read_text())
                assignment = next(node for node in tree.body if isinstance(node, ast.Assign))
                self.assertEqual(assignment.targets[0].id, "go_sdk")
                self.assertEqual(assignment.value.func.id, "use_extension")
                self.assertEqual([ast.literal_eval(arg) for arg in assignment.value.args],
                                 [f"@{alias or 'rules_go'}//go:extensions.bzl", "go_sdk"])
                download = tree.body[-1].value
                self.assertEqual((download.func.value.id, download.func.attr), ("go_sdk", "download"))
                self.assertEqual({kw.arg: ast.literal_eval(kw.value) for kw in download.keywords},
                                 {"version": "1.25.0"})
                self.assertEqual(json.loads((artifacts / "validation.json").read_text())["go_sdk"],
                                 {"version": "1.25.0"})

    def test_absent_go_sdk_preserves_default_consumer_declarations(self) -> None:
        artifacts = self.run_fixture("default-sdk")
        self.assertNotIn("go_sdk", (artifacts / "consumer.MODULE.bazel").read_text())
        self.assertIsNone(json.loads((artifacts / "validation.json").read_text())["go_sdk"])

    def test_rust_toolchain_uses_declared_repository_and_retains_selection(self) -> None:
        for alias in (None, "rs_rules"):
            with self.subTest(alias=alias):
                dependency = {"name": "rules_rs", "version": "0.1.0"}
                if alias:
                    dependency["repo_name"] = alias
                self.config["consumer_deps"] = [dependency]
                self.config["rust_toolchain"] = {"version": "1.90.0"}
                write_json(self.config_path, self.config)
                fetched = self.fetched_module("rules_rs")
                fetched.parent.mkdir(exist_ok=True)
                fetched.write_text('module(name = "rules_rs", version = "0.1.0")\n')
                artifacts = self.run_fixture(alias or "default-rust-alias")
                tree = ast.parse((artifacts / "consumer.MODULE.bazel").read_text())
                assignment = next(node for node in tree.body if isinstance(node, ast.Assign))
                self.assertEqual(assignment.targets[0].id, "rust")
                self.assertEqual(assignment.value.func.id, "use_extension")
                self.assertEqual([ast.literal_eval(arg) for arg in assignment.value.args],
                                 [f"@{alias or 'rules_rs'}//rs:rules_rust_reexported_extensions.bzl", "rust"])
                toolchain = next(node.value for node in tree.body if isinstance(node, ast.Expr)
                                 and isinstance(node.value.func, ast.Attribute))
                self.assertEqual((toolchain.func.value.id, toolchain.func.attr), ("rust", "toolchain"))
                self.assertEqual({kw.arg: ast.literal_eval(kw.value) for kw in toolchain.keywords}, {
                    "edition": "2021", "versions": ["1.90.0"],
                    "extra_target_triples": ["aarch64-unknown-linux-gnu", "x86_64-unknown-linux-gnu"],
                })
                self.assertEqual(json.loads((artifacts / "validation.json").read_text())["rust_toolchain"],
                                 {"version": "1.90.0"})
                self.assertIn('register_toolchains("@rust_toolchains//:all")',
                              (artifacts / "consumer.MODULE.bazel").read_text())

    def test_rust_native_link_and_bindgen_support_are_explicit(self) -> None:
        self.config["consumer_deps"] = [{"name": "rules_rs", "version": "0.1.0", "repo_name": "rs_rules"}]
        self.config["rust_toolchain"] = {
            "version": "1.90.0", "mangled_allocator_libraries": True, "bindgen": True,
        }
        write_json(self.config_path, self.config)
        fetched = self.fetched_module("rules_rs")
        fetched.parent.mkdir()
        fetched.write_text('module(name = "rules_rs", version = "0.1.0")\n')
        with mock.patch.object(registry_ci, "run_logged", wraps=registry_ci.run_logged) as execute:
            artifacts = self.run_fixture("rust-native-support")
        declarations = (artifacts / "consumer.MODULE.bazel").read_text()
        self.assertIn('@rs_rules//rs:rules_rust.bzl', declarations)
        self.assertIn('use_repo(rules_rust, "rules_rust")', declarations)
        self.assertIn('@rs_rules//rs:rules_rust_bindgen.bzl', declarations)
        self.assertIn('register_toolchains("@rules_rust_bindgen//:all")', declarations)
        for call in execute.call_args_list:
            self.assertIn("--@rules_rust//rust/settings:experimental_use_allocator_libraries_with_mangled_symbols=True",
                          call.args[0])
        self.assertEqual(json.loads((artifacts / "validation.json").read_text())["rust_toolchain"],
                         self.config["rust_toolchain"])

    def test_absent_rust_toolchain_preserves_default_consumer_declarations(self) -> None:
        with mock.patch.object(registry_ci, "run_logged", wraps=registry_ci.run_logged) as execute:
            artifacts = self.run_fixture("no-rust-toolchain")
        declarations = (artifacts / "consumer.MODULE.bazel").read_text()
        self.assertNotIn("rust", declarations)
        self.assertIsNone(json.loads((artifacts / "validation.json").read_text())["rust_toolchain"])
        for call in execute.call_args_list:
            self.assertFalse(any("mangled_symbols" in argument for argument in call.args[0]))

    def test_empty_consumer_dependencies_need_no_overrides_or_dependency_artifacts(self) -> None:
        self.config["consumer_deps"] = []
        self.config["platforms"] = {"amd64": "@alpha//:platform"}
        write_json(self.config_path, self.config)
        artifacts = self.run_fixture("empty-dependencies")
        self.assertEqual(self.declarations(artifacts, "single_version_override"), [])
        self.assertEqual(self.declarations(artifacts, "bazel_dep"), [{"name": "alpha", "version": "1.0.0"}])
        self.assertEqual(json.loads((artifacts / "validation.json").read_text())["consumer_deps"], [])
        self.assertEqual(list(artifacts.glob("consumer-dep-*.MODULE.bazel")), [])

    def test_missing_generated_lockfile_cannot_pass_validation(self) -> None:
        self.fake_bazel.write_text("\n".join(
            line for line in self.fake_bazel.read_text().splitlines()
            if "Path('MODULE.bazel.lock').write_text" not in line
        ) + "\n")
        with self.assertRaisesRegex(registry_ci.RegistryError, "did not generate MODULE.bazel.lock"):
            self.run_fixture("missing-lockfile")
        self.assertFalse((self.root / "artifacts-missing-lockfile" / "validation.json").exists())

    def test_extension_repositories_do_not_count_as_fetched_modules(self) -> None:
        for name in ("alpha", "sonic-build-infra"):
            path = self.output_base / "external" / (name + "++extension+generated") / "MODULE.bazel"
            path.parent.mkdir()
            path.write_text('module(name = "generated", version = "9.0.0")\n')
        artifacts = self.run_fixture("extension-repositories")
        self.assertTrue(json.loads((artifacts / "validation.json").read_text())["fetched_module_matches_registry"])

    def test_duplicate_real_module_repositories_are_rejected(self) -> None:
        path = self.output_base / "external/alpha+1.0.0/MODULE.bazel"
        path.parent.mkdir()
        path.write_bytes(self.fetched.read_bytes())
        with self.assertRaisesRegex(registry_ci.RegistryError, "Expected one fetched repository for alpha"):
            self.run_fixture("duplicate-module")

    def test_generated_lockfile_is_retained_after_bazel_failure(self) -> None:
        self.fake_bazel.write_text(self.fake_bazel.read_text().replace(
            "elif 'test' in args:", "elif 'test' in args:\n    sys.exit(42)"
        ))
        with self.assertRaisesRegex(registry_ci.RegistryError, "status 42"):
            self.run_fixture("failed-bazel")
        artifacts = self.root / "artifacts-failed-bazel"
        self.assertEqual(json.loads((artifacts / "MODULE.bazel.lock").read_text()), {"lockFileVersion": 13})
        self.assertFalse((artifacts / "validation.json").exists())

    def test_action_logs_are_retained_when_build_or_test_fails(self) -> None:
        original = self.fake_bazel.read_text()
        for phase in ("build", "test"):
            with self.subTest(phase=phase):
                failure = "\n".join([
                    "    output = Path.cwd() / 'failed-stdout'",
                    "    output.write_text('actual compiler error\\n')",
                    "    bep = next(arg.split('=', 1)[1] for arg in args if arg.startswith('--build_event_json_file='))",
                    "    Path(bep).write_text(json.dumps({'action': {'exitCode': 42, 'stdout': {'uri': output.as_uri()}}}) + '\\n')",
                    "    sys.exit(42)",
                ])
                self.fake_bazel.write_text(original.replace(
                    f"elif '{phase}' in args:", f"elif '{phase}' in args:\n{failure}"
                ))
                with self.assertRaisesRegex(registry_ci.RegistryError, "status 42"):
                    self.run_fixture(f"action-failure-{phase}")
                artifacts = self.root / f"artifacts-action-failure-{phase}"
                records = json.loads((artifacts / f"failed-actions/{phase}-events/index.json").read_text())
                self.assertEqual((artifacts / records[0]["path"]).read_text(), "actual compiler error\n")
                self.assertFalse((artifacts / "validation.json").exists())

    def test_mismatched_or_missing_fetched_consumer_dependencies_are_rejected(self) -> None:
        for dependency in self.config["consumer_deps"]:
            name, version = dependency["name"], dependency["version"]
            path = self.fetched_module(name)
            original = path.read_text()
            for case, contents in (
                ("wrong-name", f'module(name = "wrong-name", version = "{version}")\n'),
                ("wrong-version", f'module(name = "{name}", version = "9.9.9")\n'),
                ("missing", None),
            ):
                with self.subTest(dependency=name, case=case):
                    if contents is None:
                        path.unlink()
                    else:
                        path.write_text(contents)
                    with self.assertRaisesRegex(registry_ci.RegistryError, f"consumer dependency {name}"):
                        self.run_fixture(f"{name}-{case}")
                    path.write_text(original)

    def test_successful_bazel_commands_cannot_hide_a_different_fetched_module(self) -> None:
        mismatches = (
            'module(name = "beta", version = "1.0.0")\n',
            'module(name = "alpha", version = "2.0.0")\n',
            'module(name = "alpha", version = "1.0.0")\nbazel_dep(name = "extra", version = "1.0.0")\n',
        )
        for index, contents in enumerate(mismatches):
            with self.subTest(contents=contents):
                self.fetched.write_text(contents)
                with self.assertRaises(registry_ci.RegistryError):
                    self.run_fixture(f"wrong-module-{index}")


if __name__ == "__main__":
    unittest.main()
