"""Regression tests for registry CI's fail-closed merge checks."""

from __future__ import annotations

import ast
import base64
import contextlib
import copy
import hashlib
import importlib.util
import io
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
    def test_new_module_validates_replacement_and_logs_yanked_version(self) -> None:
        (self.root / "README.md").write_text("Registry\n")
        base = self.commit("before module registration")
        old = self.entry("alpha", "1.0.0")
        self.entry("alpha", "2.0.0")
        path = old.parent / "metadata.json"
        metadata = json.loads(path.read_text())
        metadata["yanked_versions"] = {"1.0.0": "Broken external launcher; use 2.0.0."}
        write_json(path, metadata)
        head = self.commit("register fixed version and retain withdrawn source")
        output = io.StringIO()
        with contextlib.redirect_stderr(output):
            self.assertEqual(self.selected(base, head), {("alpha", "2.0.0")})
        self.assertIn("Skipping execution of yanked alpha@1.0.0", output.getvalue())
        self.assertIn("Broken external launcher; use 2.0.0.", output.getvalue())

    def test_metadata_yank_and_infrastructure_changes_keep_active_versions(self) -> None:
        old = self.entry("alpha", "1.0.0")
        self.entry("alpha", "2.0.0")
        base = self.commit("two active versions")
        path = old.parent / "metadata.json"
        metadata = json.loads(path.read_text())
        metadata["yanked_versions"] = {"1.0.0": "Broken launcher."}
        write_json(path, metadata)
        head = self.commit("withdraw old version")
        self.assertEqual(self.selected(base, head), {("alpha", "2.0.0")})
        jobs = registry_ci.plan(self.root, None, None, all_versions=True)["include"]
        self.assertEqual({(job["module"], job["version"]) for job in jobs}, {("alpha", "2.0.0")})
        (self.root / "ci").mkdir()
        (self.root / "ci" / "registry_ci.py").write_text("changed runner\n")
        changed = self.commit("change infrastructure")
        self.assertEqual(self.selected(head, changed), {("alpha", "2.0.0")})

    def test_yanked_version_still_requires_valid_source_integrity_and_manifest(self) -> None:
        entry = self.entry("alpha", "1.0.0")
        write_json(entry.parent / "metadata.json", {
            "versions": ["1.0.0"], "yanked_versions": {"1.0.0": "Broken launcher."},
        })
        source_path = entry / "source.json"
        source = json.loads(source_path.read_text())
        for field, value in (("integrity", "sha256-invalid"), ("url", "file:///local/archive")):
            with self.subTest(field=field):
                write_json(source_path, {**source, field: value})
                with self.assertRaises(registry_ci.RegistryError):
                    registry_ci.plan(self.root, None, None, all_versions=True)
        write_json(source_path, source)
        write_json(entry / "presubmit.json", {})
        with self.assertRaises(registry_ci.RegistryError):
            registry_ci.plan(self.root, None, None, all_versions=True)

    def test_yanked_version_still_rejects_corrupted_or_escaping_registry_inputs(self) -> None:
        entry = self.entry("alpha", "1.0.0")
        write_json(entry.parent / "metadata.json", {
            "versions": ["1.0.0"], "yanked_versions": {"1.0.0": "Broken launcher."},
        })
        source_path = entry / "source.json"
        source = json.loads(source_path.read_text())
        for field in ("patches", "overlay"):
            with self.subTest(field=field):
                folder = entry / field
                folder.mkdir()
                (folder / "input").write_bytes(b"changed bytes")
                write_json(source_path, {**source, field: {"input": digest(b"original bytes")}})
                with self.assertRaisesRegex(registry_ci.RegistryError, "Integrity checksum mismatch"):
                    registry_ci.plan(self.root, None, None, all_versions=True)
                write_json(source_path, {**source, field: {"../outside": digest(b"original bytes")}})
                with self.assertRaisesRegex(registry_ci.RegistryError, "Unsafe registry input path"):
                    registry_ci.plan(self.root, None, None, all_versions=True)
                shutil.rmtree(folder)

    def test_yanked_version_cannot_hide_a_missing_directory(self) -> None:
        entry = self.entry("alpha", "1.0.0")
        base = self.commit("published version")
        shutil.rmtree(entry)
        write_json(entry.parent / "metadata.json", {
            "versions": ["1.0.0"], "yanked_versions": {"1.0.0": "Broken launcher."},
        })
        head = self.commit("invalid deletion")
        with self.assertRaises(registry_ci.RegistryError):
            registry_ci.plan(self.root, base, head)

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
    def test_yanked_metadata_requires_known_versions_and_nonempty_reasons(self) -> None:
        entry = self.entry("alpha", "1.0.0")
        cases = (None, [], ["1.0.0"], {"2.0.0": "Unknown version."},
                 {"1.0.0": None}, {"1.0.0": False}, {"1.0.0": ""}, {"1.0.0": " \n"})
        for yanked in cases:
            with self.subTest(yanked=yanked):
                write_json(entry.parent / "metadata.json", {"versions": ["1.0.0"], "yanked_versions": yanked})
                with self.assertRaisesRegex(registry_ci.RegistryError, "yanked_versions"):
                    registry_ci.validate_entry(self.root, "alpha", "1.0.0")

    def test_yanked_version_cannot_be_run_directly(self) -> None:
        entry = self.entry("alpha", "1.0.0")
        write_json(entry.parent / "metadata.json", {
            "versions": ["1.0.0"], "yanked_versions": {"1.0.0": "Broken launcher."},
        })
        work = self.root / "work"
        artifacts = self.root / "artifacts"
        with self.assertRaisesRegex(registry_ci.RegistryError, "Cannot execute validation for yanked alpha@1.0.0"):
            registry_ci.run(self.root, "alpha", "1.0.0", "amd64", work, artifacts, "must-not-execute")
        self.assertFalse(work.exists())
        self.assertFalse(artifacts.exists())

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
        self.assertEqual((artifacts / "fetched.MODULE.bazel").read_bytes(), self.fetched.read_bytes())
        for dependency in self.config["consumer_deps"]:
            name = dependency["name"]
            self.assertEqual((artifacts / f"consumer-dep-{name}.MODULE.bazel").read_bytes(),
                             self.fetched_module(name).read_bytes())
        self.assertFalse((artifacts / "consumer-dep-sonic_build_infra.MODULE.bazel").exists())
        outputs = json.loads((artifacts / "outputs.json").read_text())
        self.assertEqual(set(outputs), {"@alpha//:library"})
        self.assertEqual((artifacts / outputs["@alpha//:library"][0]["path"]).read_bytes(), b"package")

    def test_empty_consumer_dependencies_need_no_overrides_or_dependency_artifacts(self) -> None:
        self.config["consumer_deps"] = []
        self.config["platforms"] = {"amd64": "@alpha//:platform"}
        write_json(self.config_path, self.config)
        artifacts = self.run_fixture("empty-dependencies")
        self.assertEqual(self.declarations(artifacts, "single_version_override"), [])
        self.assertEqual(self.declarations(artifacts, "bazel_dep"), [{"name": "alpha", "version": "1.0.0"}])
        self.assertEqual(json.loads((artifacts / "validation.json").read_text())["consumer_deps"], [])
        self.assertEqual(list(artifacts.glob("consumer-dep-*.MODULE.bazel")), [])

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
