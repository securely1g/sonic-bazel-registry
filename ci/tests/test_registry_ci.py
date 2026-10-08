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


def patched_dependency(name: str, module: bytes) -> dict:
    return {
        "name": name,
        "version": "1.0.0",
        "archive_override": {
            "urls": ["https://example.invalid/releases/source-1.0.0.tar.gz"],
            "integrity": digest(b"source archive"),
            "strip_prefix": "source-1.0.0",
            "remote_patches": {
                "https://example.invalid/source/0123456789abcdef/fix.patch": digest(b"reviewed patch"),
            },
            "remote_patch_strip": 1,
        },
        "module_sha256": hashlib.sha256(module).hexdigest(),
    }


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
    def test_manual_selection_runs_only_the_requested_entry_on_its_configured_architectures(self) -> None:
        self.entry("alpha", "1.0.0")
        requested = self.entry("alpha", "2.0.0")
        self.entry("beta", "1.0.0")
        config = json.loads((requested / "presubmit.json").read_text())
        config["architectures"] = ["amd64", "arm64"]
        config["platforms"]["arm64"] = "@platforms//host:host"
        write_json(requested / "presubmit.json", config)
        self.assertEqual(registry_ci.plan(self.root, None, None, module="alpha", version="2.0.0"), {
            "include": [
                {"module": "alpha", "version": "2.0.0", "architecture": "amd64", "runner": "ubuntu-24.04"},
                {"module": "alpha", "version": "2.0.0", "architecture": "arm64", "runner": "ubuntu-24.04-arm"},
            ],
        })

    def test_manual_selection_requires_a_pair_and_cannot_replace_another_plan_mode(self) -> None:
        for kwargs in ({"module": "alpha"}, {"version": "1.0.0"},
                       {"module": "alpha", "version": "1.0.0", "all_versions": True},
                       {"module": "alpha", "version": "1.0.0", "base": "a" * 40, "head": "b" * 40}):
            with self.subTest(kwargs=kwargs), self.assertRaises(registry_ci.RegistryError):
                registry_ci.plan(self.root, **{"base": None, "head": None, **kwargs})

    def test_manual_selection_rejects_missing_or_invalid_entries(self) -> None:
        entry = self.entry("alpha", "1.0.0")
        for module, version in (("missing", "1.0.0"), ("alpha", "9.9.9"), ("../alpha", "1.0.0")):
            with self.subTest(module=module, version=version), self.assertRaises(registry_ci.RegistryError):
                registry_ci.plan(self.root, None, None, module=module, version=version)
        (entry / "presubmit.json").unlink()
        with self.assertRaises(registry_ci.RegistryError):
            registry_ci.plan(self.root, None, None, module="alpha", version="1.0.0")

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
    def test_archive_override_requires_checksums_and_only_supported_attributes(self) -> None:
        entry = self.entry("alpha", "1.0.0")
        path = entry / "presubmit.json"
        config = json.loads(path.read_text())
        dependency = patched_dependency("platforms", b'module(name = "platforms")\n')
        config["consumer_deps"] = [dependency]
        write_json(path, config)
        self.assertEqual(registry_ci.validate_entry(self.root, "alpha", "1.0.0"), config)
        invalid_overrides = (
            {"urls": []},
            {"urls": ["http://example.invalid/source.tar.gz"]},
            {"urls": ["file:///tmp/source.tar.gz"]},
            {"urls": ["https://user:password@example.invalid/source.tar.gz"]},
            {"urls": ["https://example.invalid/source.tar.gz#fragment"]},
            {"urls": ["https://["]},
            {"urls": ["https://example.invalid/source.tar.gz"] * 2},
            {"urls": [None]},
            {"integrity": "sha256-not-a-digest"},
            {"strip_prefix": "../outside"},
            {"strip_prefix": "/absolute"},
            {"remote_patches": ["https://example.invalid/fix.patch"]},
            {"remote_patches": {"http://example.invalid/fix.patch": digest(b"patch")}},
            {"remote_patches": {"https://example.invalid/fix.patch": "unchecked"}},
            {"remote_patch_strip": -1},
            {"remote_patch_strip": True},
            {"patches": ["//:unchecked.patch"]},
            {"patch_cmds": ["echo unchecked"]},
        )
        for changes in invalid_overrides:
            with self.subTest(changes=changes):
                invalid = copy.deepcopy(config)
                invalid["consumer_deps"][0]["archive_override"].update(changes)
                write_json(path, invalid)
                with self.assertRaises(registry_ci.RegistryError):
                    registry_ci.validate_entry(self.root, "alpha", "1.0.0")
        for removed in ("urls", "integrity"):
            invalid = copy.deepcopy(config)
            del invalid["consumer_deps"][0]["archive_override"][removed]
            write_json(path, invalid)
            with self.assertRaises(registry_ci.RegistryError):
                registry_ci.validate_entry(self.root, "alpha", "1.0.0")

    def test_archive_override_and_patched_module_hash_are_required_together(self) -> None:
        entry = self.entry("alpha", "1.0.0")
        path = entry / "presubmit.json"
        config = json.loads(path.read_text())
        dependency = patched_dependency("platforms", b'module(name = "platforms")\n')
        for removed in ("archive_override", "module_sha256"):
            invalid = copy.deepcopy(dependency)
            del invalid[removed]
            config["consumer_deps"] = [invalid]
            write_json(path, config)
            with self.assertRaisesRegex(registry_ci.RegistryError, "supplied together"):
                registry_ci.validate_entry(self.root, "alpha", "1.0.0")
        for value in (None, "", "f" * 63, "G" * 64, "F" * 64):
            config["consumer_deps"] = [{**dependency, "module_sha256": value}]
            write_json(path, config)
            with self.assertRaisesRegex(registry_ci.RegistryError, "module_sha256"):
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

    def run_fixture(self, suffix: str) -> Path:
        artifacts = self.root / f"artifacts-{suffix}"
        registry_ci.run(
            self.root, "alpha", "1.0.0", "amd64",
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

    def test_archive_override_uses_patched_source_instead_of_a_registry_version(self) -> None:
        module = b'module(name = "sonic-build-infra")\n# Patched source can omit its version.\n'
        dependency = patched_dependency("sonic-build-infra", module)
        dependency["repo_name"] = "sonic_build_infra"
        self.config["consumer_deps"][1] = dependency
        write_json(self.config_path, self.config)
        self.fetched_module(dependency["name"]).write_bytes(module)
        artifacts = self.run_fixture("patched-source")
        self.assertEqual(self.declarations(artifacts, "archive_override"), [
            {"module_name": dependency["name"], **dependency["archive_override"]},
        ])
        self.assertEqual(self.declarations(artifacts, "single_version_override"), [
            {"module_name": "platforms", "version": "1.0.0"},
        ])
        self.assertEqual(self.declarations(artifacts, "bazel_dep")[-1], {
            "name": "sonic-build-infra", "version": "1.0.0", "repo_name": "sonic_build_infra",
        })
        self.assertEqual(json.loads((artifacts / "validation.json").read_text())["consumer_deps"],
                         self.config["consumer_deps"])
        self.assertEqual((artifacts / "consumer-dep-sonic-build-infra.MODULE.bazel").read_bytes(), module)

    def test_archive_override_rejects_unpatched_source_even_after_successful_bazel_commands(self) -> None:
        module = self.fetched_module("sonic-build-infra").read_bytes()
        self.config["consumer_deps"][1] = patched_dependency("sonic-build-infra", module + b"# Patched\n")
        write_json(self.config_path, self.config)
        with self.assertRaisesRegex(registry_ci.RegistryError, "patched MODULE.bazel SHA256"):
            self.run_fixture("unpatched-source")
        self.assertFalse((self.root / "artifacts-unpatched-source" / "validation.json").exists())

    def test_archive_override_still_checks_the_module_name(self) -> None:
        wrong_module = b'module(name = "wrong-name")\n'
        self.config["consumer_deps"][1] = patched_dependency("sonic-build-infra", wrong_module)
        write_json(self.config_path, self.config)
        self.fetched_module("sonic-build-infra").write_bytes(wrong_module)
        with self.assertRaisesRegex(registry_ci.RegistryError, "different module name"):
            self.run_fixture("patched-wrong-name")

    def test_registry_dependency_still_requires_a_declared_version(self) -> None:
        self.fetched_module("sonic-build-infra").write_text('module(name = "sonic-build-infra")\n')
        with self.assertRaisesRegex(registry_ci.RegistryError, "needs literal name and version"):
            self.run_fixture("missing-registry-version")

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
