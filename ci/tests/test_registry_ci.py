"""Regression tests for registry CI's fail-closed merge checks."""

from __future__ import annotations

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


class FetchedModuleTests(FixtureTestCase):
    def test_successful_bazel_commands_cannot_hide_a_different_fetched_module(self) -> None:
        entry = self.entry("alpha", "1.0.0")
        config_path = entry / "presubmit.json"
        config = json.loads(config_path.read_text())
        config["build_flags"] = ["--@alpha//bazel:yang_modules=False"]
        write_json(config_path, config)
        output_base = self.root / "fake-output-base"
        fetched = output_base / "external" / "alpha+" / "MODULE.bazel"
        fetched.parent.mkdir(parents=True)
        fake_bazel = self.root / "fake-bazel"
        fake_bazel.write_text(
            "#!/usr/bin/env python3\n"
            "import json\n"
            "from pathlib import Path\n"
            "import sys\n"
            "args = sys.argv[1:]\n"
            "assert '--@alpha//bazel:yang_modules=False' in args\n"
            "if 'info' in args:\n"
            f"    print({str(output_base)!r})\n"
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
        fake_bazel.chmod(0o755)
        # A successful control proves build/test/info receive the feature
        # setting and that later failures really come from module identity.
        fetched.write_bytes((entry / "MODULE.bazel").read_bytes())
        registry_ci.run(
            self.root, "alpha", "1.0.0", "amd64",
            self.root / "work-control", self.root / "artifacts-control", str(fake_bazel),
        )
        validation = json.loads((self.root / "artifacts-control" / "validation.json").read_text())
        self.assertEqual(validation["build_flags"], config["build_flags"])
        mismatches = (
            'module(name = "beta", version = "1.0.0")\n',
            'module(name = "alpha", version = "1.0.0")\nbazel_dep(name = "extra", version = "1.0.0")\n',
        )
        for index, contents in enumerate(mismatches):
            with self.subTest(contents=contents):
                fetched.write_text(contents)
                with self.assertRaises(registry_ci.RegistryError):
                    registry_ci.run(
                        self.root, "alpha", "1.0.0", "amd64",
                        self.root / f"work-{index}", self.root / f"artifacts-{index}", str(fake_bazel),
                    )


if __name__ == "__main__":
    unittest.main()
