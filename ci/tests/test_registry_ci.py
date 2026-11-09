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
import re
import shutil
import subprocess
import sys
import tarfile
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

    def selected(self, base: str, head: str, published: str | None = None) -> set[tuple[str, str]]:
        return {
            (job["module"], job["version"])
            for job in registry_ci.plan(self.root, base, head, published=published or base)["include"]
        }


class SelectionTests(FixtureTestCase):
    def test_advanced_base_release_does_not_select_absent_history(self) -> None:
        self.entry("alpha", "1.0.0", configured=False)
        self.entry("alpha", "2.0.0")
        ancestor = self.commit("published registry with legacy version")
        self.git("checkout", "-b", "published-advance")
        self.entry("alpha", "3.0.0")
        base = self.commit("publish another release after topic fork")
        self.git("checkout", "-b", "ci-topic", ancestor)
        ci = self.root / "ci" / "runner.py"
        ci.parent.mkdir()
        ci.write_text("# topic runner change\n")
        head = self.commit("change CI on older checkout")
        self.assertEqual(self.selected(base, head), {("alpha", "2.0.0")})

    def test_advanced_base_module_is_not_a_topic_deletion(self) -> None:
        self.entry("alpha", "1.0.0")
        ancestor = self.commit("published alpha")
        self.git("checkout", "-b", "published-module")
        self.entry("beta", "1.0.0")
        base = self.commit("publish unrelated module after topic fork")
        self.git("checkout", "-b", "alpha-topic", ancestor)
        self.entry("alpha", "2.0.0")
        head = self.commit("add the single alpha candidate")
        self.assertEqual(self.selected(base, head), {("alpha", "2.0.0")})

    def test_changed_version_is_selected_without_unrelated_versions(self) -> None:
        self.entry("alpha", "1.0.0")
        self.entry("beta", "1.0.0")
        published = self.commit("published registry")
        changed = self.entry("alpha", "2.0.0")
        base = self.commit("unreleased candidate")
        (changed / "README.md").write_text("Updated module instructions.\n")
        head = self.commit("change alpha version")
        self.assertEqual(self.selected(base, head, published), {("alpha", "2.0.0")})

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
            registry_ci.plan(self.root, base, head, published=base)

    def test_changed_standalone_tests_without_manifest_fail_planning(self) -> None:
        entry = self.entry("alpha", "1.0.0", configured=False)
        base = self.commit("historical unconfigured version")
        (entry / "tests").mkdir()
        (entry / "tests" / "consumer_test.py").write_text("assert True\n")
        head = self.commit("add test without a validation manifest")
        with self.assertRaisesRegex(registry_ci.RegistryError, "presubmit.json"):
            registry_ci.plan(self.root, base, head, published=base)

    def test_deleted_version_fails_planning(self) -> None:
        entry = self.entry("alpha", "1.0.0")
        base = self.commit("initial registry")
        shutil.rmtree(entry)
        write_json(entry.parent / "metadata.json", {"versions": []})
        head = self.commit("delete version")
        with self.assertRaises(registry_ci.RegistryError):
            registry_ci.plan(self.root, base, head, published=base)

    def test_renaming_version_cannot_hide_deleted_version(self) -> None:
        entry = self.entry("alpha", "1.0.0")
        base = self.commit("initial registry")
        renamed = entry.with_name("2.0.0")
        entry.rename(renamed)
        (renamed / "MODULE.bazel").write_text('module(name = "alpha", version = "2.0.0")\n')
        write_json(renamed.parent / "metadata.json", {"versions": ["2.0.0"]})
        head = self.commit("rename version")
        with self.assertRaises(registry_ci.RegistryError):
            registry_ci.plan(self.root, base, head, published=base)

    def test_infrastructure_changes_select_latest_configured_modules(self) -> None:
        self.entry("alpha", "1.0.0")
        self.entry("alpha", "2.0.0")
        self.entry("beta", "2.0.0")
        self.entry("legacy", "1.0.0", configured=False)
        paths = [
            self.root / "ci" / "registry_ci.py",
            self.root / ".github" / "workflows" / "registry.yml",
            self.root / ".github" / "workflows" / "registry-module.yml",
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
                self.assertEqual(self.selected(base, head), {("alpha", "2.0.0"), ("beta", "2.0.0")})
                base = head

    def test_all_mode_keeps_configured_historical_versions(self) -> None:
        self.entry("alpha", "1.0.0")
        self.entry("alpha", "2.0.0")
        self.entry("legacy", "1.0.0", configured=False)
        head = self.commit("published registry")
        jobs = registry_ci.plan(self.root, None, head, all_versions=True, published=head)["include"]
        self.assertEqual({(job["module"], job["version"]) for job in jobs},
                         {("alpha", "1.0.0"), ("alpha", "2.0.0")})

    def latest_selected(self) -> set[tuple[str, str]]:
        head = self.commit("published registry")
        return {(job["module"], job["version"])
                for job in registry_ci.plan(self.root, None, head, latest_versions=True, published=head)["include"]}

    def test_latest_mode_selects_one_version_and_retains_native_architectures(self) -> None:
        self.entry("alpha", "1.0.0")
        latest = self.entry("alpha", "2.0.0")
        self.entry("beta", "1.0.0")
        self.entry("legacy", "1.0.0", configured=False)
        config = json.loads((latest / "presubmit.json").read_text())
        config["architectures"].append("arm64")
        config["platforms"]["arm64"] = "@platforms//host:host"
        write_json(latest / "presubmit.json", config)
        head = self.commit("published registry")
        with mock.patch.object(registry_ci, "ARM_CROSS_ALL", False):
            jobs = registry_ci.plan(self.root, None, head, latest_versions=True, published=head)["include"]
        self.assertEqual({(job["module"], job["version"], job["architecture"], tuple(job["runner"]))
                          for job in jobs}, {
            ("alpha", "2.0.0", "amd64", ("self-hosted", "Linux", "X64", "debian-trixie-container")),
            ("alpha", "2.0.0", "arm64", ("ubuntu-24.04-arm",)),
            ("beta", "1.0.0", "amd64", ("self-hosted", "Linux", "X64", "debian-trixie-container")),
        })

    def test_latest_compares_release_and_sonic_patch_numbers_numerically(self) -> None:
        cases = {
            "release": (["0.0.10", "0.0.9"], "0.0.10"),
            "patch": (["0.9.4.sonic.10", "0.9.4.sonic.9"], "0.9.4.sonic.10"),
            "legacy_patch": (["0.9.4-sonic.10", "0.9.4-sonic.9"], "0.9.4-sonic.10"),
            "patch_migration": (["0.9.4.sonic.1", "0.9.4-sonic.1"], "0.9.4.sonic.1"),
            "release_before_patch": (["0.9.5.sonic.1", "0.9.4.sonic.99"], "0.9.5.sonic.1"),
            "four_components": (["1.8.0.10.sonic.1", "1.8.0.3.sonic.9"], "1.8.0.10.sonic.1"),
        }
        for module, (versions, _) in cases.items():
            for version in versions:
                self.entry(module, version)
        self.assertEqual(self.latest_selected(),
                         {(module, expected) for module, (_, expected) in cases.items()})

    def test_latest_source_snapshot_uses_registration_order_not_hash_order(self) -> None:
        old = "0.0.18-" + "f" * 40
        current = "0.0.18-" + "1" * 40
        self.entry("infra", old)
        self.entry("infra", current)
        # A later registration of an older release must not replace 0.0.18.
        self.entry("infra", "0.0.8-" + "e" * 40)
        self.entry("short_hash", "1.0.0-fffffff")
        self.entry("short_hash", "1.0.0-1111111")
        self.assertEqual(self.latest_selected(),
                         {("infra", current), ("short_hash", "1.0.0-1111111")})

    def test_latest_handles_published_sonic_go_snapshot_versions(self) -> None:
        # openconfig_goyang's published form previously prevented the entire
        # latest-module matrix from being planned.
        current = "0.0.0.sonic.1-20200309174518-a00bece872fc"
        self.entry("goyang", current)
        self.entry("numeric_patch", "0.0.0.sonic.10-20200309174518-a00bece872fc")
        self.entry("numeric_patch", "0.0.0.sonic.9-20260309174518-ffffffffffff")
        self.entry("registration_order", "0.0.0.sonic.1-20260309174518-ffffffffffff")
        self.entry("registration_order", current)
        self.assertEqual(self.latest_selected(), {
            ("goyang", current),
            ("numeric_patch", "0.0.0.sonic.10-20200309174518-a00bece872fc"),
            ("registration_order", current),
        })

    def test_latest_rejects_malformed_sonic_go_snapshot_suffixes(self) -> None:
        for version in (
            "0.0.0.sonic.1-20200309-a00bece872fc",
            "0.0.0.sonic.1-20200309174518-not-a-commit",
            "0.0.0.sonic.1-20200309174518-a00bece872fc-extra",
        ):
            with self.subTest(version=version):
                with self.assertRaisesRegex(registry_ci.RegistryError, "Unsupported registry version"):
                    registry_ci.release_key(version)

    def test_latest_handles_legacy_registry_version_names(self) -> None:
        historical = {
            "old_buildimage": "3.7.0.sonic-buildimage",
            "old_patched": "0.60.0.sonic-patched",
            "old_commit": "0.0.0.commit-" + "a" * 40,
        }
        for module, version in historical.items():
            self.entry(module, version, configured=False)
            self.entry(module, "9.0.0.sonic.1")
        self.assertEqual(self.latest_selected(),
                         {(module, "9.0.0.sonic.1") for module in historical})

    def test_ci_change_also_tests_directly_changed_older_candidate(self) -> None:
        self.entry("alpha", "2.0.0")
        self.entry("beta", "1.0.0")
        published = self.commit("published registry")
        old = self.entry("alpha", "1.0.0")
        base = self.commit("unreleased older candidate")
        ci = self.root / "ci" / "registry_ci.py"
        ci.parent.mkdir()
        ci.write_text("changed planner\n")
        (old / "README.md").write_text("Changed older version.\n")
        head = self.commit("change CI and historical alpha")
        self.assertEqual(self.selected(base, head, published=published),
                         {("alpha", "1.0.0"), ("alpha", "2.0.0"), ("beta", "1.0.0")})

    def test_latest_does_not_fall_back_when_newest_version_has_no_manifest(self) -> None:
        self.entry("alpha", "1.0.0")
        self.entry("alpha", "2.0.0", configured=False)
        with self.assertRaises(registry_ci.RegistryError):
            self.latest_selected()

    def test_latest_omits_modules_with_no_configured_versions(self) -> None:
        self.entry("legacy", "1.0.0", configured=False)
        self.entry("legacy", "2.0.0", configured=False)
        self.assertEqual(self.latest_selected(), set())

    def test_latest_skips_yanked_versions_but_all_mode_preserves_them(self) -> None:
        entry = self.entry("alpha", "1.0.0")
        self.entry("alpha", "2.0.0")
        write_json(entry.parent / "metadata.json", {
            "versions": ["1.0.0", "2.0.0"],
            "yanked_versions": {"2.0.0": "Regression in the newer release"},
        })
        self.assertEqual(self.latest_selected(), {("alpha", "1.0.0")})
        head = self.git("rev-parse", "HEAD")
        jobs = registry_ci.plan(self.root, None, head, all_versions=True, published=head)["include"]
        self.assertEqual({(job["module"], job["version"]) for job in jobs},
                         {("alpha", "1.0.0"), ("alpha", "2.0.0")})

    def test_latest_omits_fully_yanked_module(self) -> None:
        entry = self.entry("alpha", "1.0.0")
        write_json(entry.parent / "metadata.json", {
            "versions": ["1.0.0"], "yanked_versions": {"1.0.0": "Withdrawn"},
        })
        self.assertEqual(self.latest_selected(), set())

    def test_direct_edit_of_published_yanked_version_is_rejected(self) -> None:
        entry = self.entry("alpha", "1.0.0")
        write_json(entry.parent / "metadata.json", {
            "versions": ["1.0.0"], "yanked_versions": {"1.0.0": "Withdrawn"},
        })
        base = self.commit("initial registry with yanked version")
        (entry / "MODULE.bazel").write_text('module(name = "alpha", version = "1.0.0")\n# Changed\n')
        head = self.commit("change yanked module declaration")
        with self.assertRaisesRegex(registry_ci.RegistryError, "published version changed"):
            self.selected(base, head)

    def test_latest_rejects_invalid_metadata_and_unlisted_configured_versions(self) -> None:
        entry = self.entry("alpha", "1.0.0")
        invalid = [
            {},
            {"versions": "1.0.0"},
            {"versions": []},
            {"versions": [1]},
            {"versions": ["1.0.0", "1.0.0"]},
            {"versions": ["2.0.0"]},
            {"versions": ["1.0.0"], "yanked_versions": []},
            {"versions": ["1.0.0"], "yanked_versions": {"2.0.0": "Unknown version"}},
        ]
        for metadata in invalid:
            with self.subTest(metadata=metadata):
                write_json(entry.parent / "metadata.json", metadata)
                with self.assertRaises(registry_ci.RegistryError):
                    self.latest_selected()

    def test_latest_rejects_unsupported_version_instead_of_guessing(self) -> None:
        self.entry("alpha", "1.0.0")
        self.entry("alpha", "next-release")
        with self.assertRaises(registry_ci.RegistryError):
            self.latest_selected()

    def test_plan_cli_supports_latest_and_explicit_historical_runs(self) -> None:
        self.entry("alpha", "1.0.0")
        self.entry("alpha", "2.0.0")
        head = self.commit("published registry")
        output = self.root / "plan.json"
        for flag, expected in (("--latest", {"2.0.0"}), ("--all", {"1.0.0", "2.0.0"})):
            with self.subTest(flag=flag):
                command = ["registry_ci.py", "plan", flag, "--published", head, "--head", head, "--output", str(output)]
                with mock.patch.object(registry_ci, "ROOT", self.root), \
                        mock.patch.object(sys, "argv", command), \
                        mock.patch.object(sys, "stdout", io.StringIO()), \
                        mock.patch.object(sys, "stderr", io.StringIO()):
                    registry_ci.main()
                jobs = json.loads(output.read_text())["include"]
                self.assertEqual({job["version"] for job in jobs}, expected)
        command = ["registry_ci.py", "plan", "--latest", "--all", "--output", str(output)]
        before = output.read_bytes()
        with mock.patch.object(registry_ci, "ROOT", self.root), \
                mock.patch.object(sys, "argv", command), \
                mock.patch.object(sys, "stderr", io.StringIO()), \
                self.assertRaises(SystemExit) as raised:
            registry_ci.main()
        self.assertNotEqual(raised.exception.code, 0)
        self.assertEqual(output.read_bytes(), before)

    def test_plan_rejects_conflicting_selection_modes(self) -> None:
        self.entry("alpha", "1.0.0")
        sha = self.commit("initial registry")
        cases = [
            (None, None, True, True),
            (sha, sha, True, False),
            (sha, sha, False, True),
            (sha, None, False, True),
        ]
        for base, head, all_versions, latest_versions in cases:
            with self.subTest(base=base, head=head, all=all_versions, latest=latest_versions):
                with self.assertRaises(registry_ci.RegistryError):
                    registry_ci.plan(self.root, base, head, all_versions, latest_versions, published=sha)

    def test_latest_and_all_modes_enforce_candidate_policy(self) -> None:
        self.entry("alpha", "1.0.0")
        published = self.commit("published registry")
        self.entry("alpha", "2.0.0")
        self.entry("alpha", "3.0.0")
        head = self.commit("two unmerged candidates")
        for mode in ("latest_versions", "all_versions"):
            with self.subTest(mode=mode):
                with self.assertRaisesRegex(registry_ci.RegistryError, "multiple unreleased candidates"):
                    registry_ci.plan(self.root, None, head, published=published, **{mode: True})

    def test_latest_and_all_modes_require_the_checked_out_head(self) -> None:
        self.entry("alpha", "1.0.0")
        published = self.commit("published registry")
        self.entry("alpha", "2.0.0")
        self.commit("unmerged candidate")
        for mode in ("latest_versions", "all_versions"):
            with self.subTest(mode=mode):
                with self.assertRaisesRegex(registry_ci.RegistryError, "Checkout HEAD differs"):
                    registry_ci.plan(self.root, None, published, published=published, **{mode: True})

    def test_no_relevant_change_produces_empty_matrix(self) -> None:
        self.entry("alpha", "1.0.0")
        base = self.commit("initial registry")
        (self.root / "README.md").write_text("Registry documentation.\n")
        head = self.commit("document registry")
        self.assertEqual(registry_ci.plan(self.root, base, head, published=base), {"include": []})
        self.assertEqual(registry_ci.plan(self.root, head, head, published=head), {"include": []})


class VersionPolicyTests(FixtureTestCase):
    """Exercise publication boundaries with real Git histories, including stacks."""

    def test_stacked_base_does_not_publish_its_inherited_candidate(self) -> None:
        """A child adding .4 must also count its parent's still-unmerged .3."""
        self.entry("libyang-python", "3.1.0.sonic.2")
        published = self.commit("maintained main")
        self.entry("libyang-python", "3.1.0.sonic.3")
        stacked_base = self.commit("parent PR")
        self.entry("libyang-python", "3.1.0.sonic.4")
        head = self.commit("child PR")
        with self.assertRaisesRegex(registry_ci.RegistryError, "multiple unreleased candidates.*sonic.3.*sonic.4"):
            registry_ci.plan(self.root, stacked_base, head, published=published)

    def test_published_previous_release_and_one_new_candidate_are_valid(self) -> None:
        """Once .3 reaches main, preserve it and validate only the new .4."""
        self.entry("libyang-python", "3.1.0.sonic.2", configured=False)
        self.entry("libyang-python", "3.1.0.sonic.3")
        published = self.commit("publish .3")
        self.entry("libyang-python", "3.1.0.sonic.4")
        head = self.commit("next candidate")
        self.assertEqual(self.selected(published, head), {("libyang-python", "3.1.0.sonic.4")})

    def test_candidate_can_be_revised_before_publication(self) -> None:
        """Editing the one unmerged candidate does not require another version."""
        self.entry("alpha", "1.0.0")
        published = self.commit("main")
        candidate = self.entry("alpha", "1.0.1")
        base = self.commit("candidate")
        (candidate / "README.md").write_text("Updated candidate description.\n")
        head = self.commit("revise candidate")
        self.assertEqual(self.selected(base, head, published), {("alpha", "1.0.1")})

    def test_replacement_selects_only_the_retained_candidate(self) -> None:
        """Replacing an inherited draft does not select it or old releases."""
        self.entry("alpha", "1.0.0", configured=False)
        published = self.commit("published legacy version")
        candidate = self.entry("alpha", "2.0.0")
        base = self.commit("parent candidate")
        shutil.rmtree(candidate)
        write_json(candidate.parent / "metadata.json", {"versions": ["1.0.0"]})
        self.entry("alpha", "3.0.0")
        head = self.commit("replace inherited candidate")
        self.assertEqual(self.selected(base, head, published), {("alpha", "3.0.0")})

    def test_removed_candidate_does_not_select_unchanged_history(self) -> None:
        """Removing the only draft leaves no version to build for this diff."""
        self.entry("alpha", "1.0.0", configured=False)
        published = self.commit("published legacy version")
        candidate = self.entry("alpha", "2.0.0")
        base = self.commit("parent candidate")
        shutil.rmtree(candidate)
        write_json(candidate.parent / "metadata.json", {"versions": ["1.0.0"]})
        head = self.commit("remove inherited candidate")
        self.assertEqual(self.selected(base, head, published), set())

    def test_replacement_keeps_explicit_historical_validation(self) -> None:
        """Diff planning is narrow; explicit --all still covers old manifests."""
        self.entry("alpha", "1.0.0")
        self.entry("alpha", "2.0.0")
        published = self.commit("published configured versions")
        candidate = self.entry("alpha", "3.0.0")
        base = self.commit("parent candidate")
        shutil.rmtree(candidate)
        write_json(candidate.parent / "metadata.json", {"versions": ["1.0.0", "2.0.0"]})
        self.entry("alpha", "4.0.0")
        head = self.commit("replace inherited candidate")
        self.assertEqual(self.selected(base, head, published), {("alpha", "4.0.0")})
        all_jobs = registry_ci.plan(self.root, None, head, all_versions=True, published=published)
        self.assertEqual({(job["module"], job["version"]) for job in all_jobs["include"]},
                         {("alpha", "1.0.0"), ("alpha", "2.0.0"), ("alpha", "4.0.0")})

    def test_new_module_cannot_introduce_multiple_versions(self) -> None:
        """The one-candidate rule also applies when main has no module yet."""
        (self.root / "README.md").write_text("Registry\n")
        published = self.commit("empty registry")
        self.entry("alpha", "1.0.0")
        self.entry("alpha", "2.0.0")
        head = self.commit("two candidates for a new module")
        with self.assertRaisesRegex(registry_ci.RegistryError, "multiple unreleased candidates"):
            registry_ci.plan(self.root, published, head, published=published)

    def test_metadata_only_child_cannot_hide_multiple_inherited_candidates(self) -> None:
        """Changing only a homepage still checks the complete proposed stack."""
        self.entry("alpha", "1.0.0")
        published = self.commit("main")
        self.entry("alpha", "2.0.0")
        entry = self.entry("alpha", "3.0.0")
        base = self.commit("two inherited candidates")
        path = entry.parent / "metadata.json"
        write_json(path, {**json.loads(path.read_text()), "homepage": "https://example.invalid/alpha"})
        head = self.commit("metadata only")
        with self.assertRaisesRegex(registry_ci.RegistryError, "multiple unreleased candidates"):
            registry_ci.plan(self.root, base, head, published=published)

    def test_unlisted_candidate_directory_cannot_evade_counting(self) -> None:
        """Directories and metadata must agree before counting new versions."""
        self.entry("alpha", "1.0.0")
        published = self.commit("main")
        self.entry("alpha", "2.0.0")
        entry = self.entry("alpha", "3.0.0")
        write_json(entry.parent / "metadata.json", {"versions": ["1.0.0", "3.0.0"]})
        head = self.commit("hide an inherited candidate")
        with self.assertRaisesRegex(registry_ci.RegistryError, "metadata and version directories differ"):
            registry_ci.plan(self.root, published, head, published=published)

    def test_published_inputs_cannot_be_edited_or_removed(self) -> None:
        """Protect consumer inputs, unknown additions, modes, and whole entries."""
        entry = self.entry("alpha", "1.0.0")
        published = self.commit("main")
        for mutation in ("edit", "add", "delete", "mode", "remove"):
            with self.subTest(mutation=mutation):
                self.git("reset", "--hard", published)
                if mutation == "edit":
                    (entry / "source.json").write_text("{}\n")
                elif mutation == "add":
                    (entry / "BUILD.bazel").write_text("# New build input\n")
                elif mutation == "delete":
                    (entry / "source.json").unlink()
                elif mutation == "mode":
                    (entry / "source.json").chmod(0o755)
                else:
                    shutil.rmtree(entry)
                    write_json(entry.parent / "metadata.json", {"versions": []})
                head = self.commit(mutation)
                with self.assertRaisesRegex(registry_ci.RegistryError, "published version changed or removed"):
                    registry_ci.plan(self.root, published, head, published=published)

    def test_published_documentation_does_not_require_historical_ci(self) -> None:
        """Maintaining docs must not require retrofitting old module tests."""
        entry = self.entry("alpha", "1.0.0", configured=False)
        (entry / "README.md").write_text("Old instructions\n")
        (entry / "PATCHES.md").write_text("Obsolete notes\n")
        published = self.commit("published version without CI")
        (entry / "README.md").write_text("Corrected instructions\n")
        (entry / "PATCHES.md").unlink()
        (entry / "docs").mkdir()
        (entry / "docs" / "example.md").write_text("A concrete consumer example\n")
        head = self.commit("maintain published documentation")
        self.assertEqual(self.selected(published, head), set())

    def test_published_standalone_tests_select_the_historical_version(self) -> None:
        """Updating an older release's tests must validate that release."""
        entry = self.entry("alpha", "1.0.0")
        tests = entry / "tests"
        tests.mkdir()
        (tests / "consumer_test.py").write_text("assert True\n")
        (tests / "obsolete_fixture.txt").write_text("old fixture\n")
        self.entry("alpha", "2.0.0")
        published = self.commit("two published releases")
        (tests / "consumer_test.py").write_text("assert 1 + 1 == 2\n")
        (tests / "obsolete_fixture.txt").unlink()
        (tests / "replacement_fixture.txt").write_text("new fixture\n")
        config = json.loads((entry / "presubmit.json").read_text())
        config["test_targets"].append("@alpha//:additional_consumer_test")
        write_json(entry / "presubmit.json", config)
        head = self.commit("maintain historical standalone tests")
        self.assertEqual(self.selected(published, head), {("alpha", "1.0.0")})

    def test_published_version_can_add_standalone_ci(self) -> None:
        """CI configuration is maintenance, even when the release predates CI."""
        entry = self.entry("alpha", "1.0.0", configured=False)
        newer = self.entry("alpha", "2.0.0")
        published = self.commit("historical release without CI")
        shutil.copy2(newer / "presubmit.json", entry / "presubmit.json")
        head = self.commit("add CI for the historical release")
        self.assertEqual(self.selected(published, head), {("alpha", "1.0.0")})

    def test_published_test_executable_bit_is_maintenance(self) -> None:
        entry = self.entry("alpha", "1.0.0")
        script = entry / "tests" / "run.sh"
        script.parent.mkdir()
        script.write_text("#!/bin/sh\nexit 0\n")
        published = self.commit("published test script")
        script.chmod(0o755)
        head = self.commit("make standalone test executable")
        self.assertEqual(self.selected(published, head), {("alpha", "1.0.0")})

    def test_published_maintenance_cannot_introduce_symlinks(self) -> None:
        entry = self.entry("alpha", "1.0.0")
        docs = entry / "docs"
        docs.mkdir()
        (docs / "guide.md").write_text("Instructions\n")
        published = self.commit("published documentation")
        for relative in ("README.md", "docs/guide.md", "tests/consumer_test.py"):
            with self.subTest(path=relative):
                self.git("reset", "--hard", published)
                self.git("clean", "-fdq")
                path = entry / relative
                path.parent.mkdir(exist_ok=True)
                path.unlink(missing_ok=True)
                path.symlink_to("../MODULE.bazel")
                head = self.commit("replace maintenance file with symlink")
                with self.assertRaisesRegex(registry_ci.RegistryError, "published version changed or removed"):
                    registry_ci.plan(self.root, published, head, published=published)

    def test_published_patch_and_overlay_docs_remain_inputs(self) -> None:
        """A README or test copied into fetched sources is not standalone CI."""
        entry = self.entry("alpha", "1.0.0")
        payloads = ["patches/README.md", "overlay/docs/guide.md", "overlay/tests/consumer_test.py"]
        source = json.loads((entry / "source.json").read_text())
        for relative in payloads:
            path = entry / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("original source input\n")
            folder, name = relative.split("/", 1)
            source.setdefault(folder, {})[name] = digest(path.read_bytes())
        write_json(entry / "source.json", source)
        published = self.commit("published fetched docs and tests")
        for relative in payloads:
            for mutation in ("edit", "delete", "mode"):
                with self.subTest(path=relative, mutation=mutation):
                    self.git("reset", "--hard", published)
                    path = entry / relative
                    if mutation == "edit":
                        path.write_text("changed source input\n")
                    elif mutation == "delete":
                        path.unlink()
                    else:
                        path.chmod(0o755)
                    head = self.commit("change fetched source input")
                    with self.assertRaisesRegex(registry_ci.RegistryError, "published version changed or removed"):
                        registry_ci.plan(self.root, published, head, published=published)

    def test_published_source_references_override_maintenance_paths(self) -> None:
        """A registry-local archive cannot become mutable by living under tests/."""
        entry = self.entry("alpha", "1.0.0")
        for relative in ("docs/source.tar.gz", "tests/source.tar.gz"):
            path = entry / relative
            path.parent.mkdir()
            path.write_bytes(b"archive")
        base = self.commit("source fixtures")
        for field, url, relative in (
            ("url", "https://example.invalid/registry/docs/source.tar.gz", "docs/source.tar.gz"),
            ("mirror_urls", "https://example.invalid/registry/tests/source.tar.gz", "tests/source.tar.gz"),
            ("url", "https://example.invalid/docs/%2e%2e/tests/source.tar.gz?raw=1", "tests/source.tar.gz"),
        ):
            with self.subTest(field=field, url=url):
                self.git("reset", "--hard", base)
                source = json.loads((entry / "source.json").read_text())
                source[field] = [url] if field == "mirror_urls" else url
                write_json(entry / "source.json", source)
                published = self.commit("publish referenced archive")
                (entry / relative).write_bytes(b"changed archive")
                head = self.commit("change archive under maintenance path")
                with self.assertRaisesRegex(registry_ci.RegistryError, "published version changed or removed"):
                    registry_ci.plan(self.root, published, head, published=published)

    def test_published_docs_url_is_informational(self) -> None:
        entry = self.entry("alpha", "1.0.0", configured=False)
        (entry / "README.md").write_text("Old documentation\n")
        source = json.loads((entry / "source.json").read_text())
        source["docs_url"] = "https://example.invalid/registry/README.md"
        write_json(entry / "source.json", source)
        published = self.commit("publish documentation link")
        (entry / "README.md").write_text("Corrected documentation\n")
        head = self.commit("maintain linked documentation")
        self.assertEqual(self.selected(published, head), set())

    def test_unknown_recipe_layout_keeps_whole_entry_immutable(self) -> None:
        entry = self.entry("alpha", "1.0.0")
        original = json.loads((entry / "source.json").read_text())
        base = self.commit("archive entry")
        for extra in ({"type": "local_path"}, {"future_build_input": "unrecognized layout"}):
            with self.subTest(extra=extra):
                self.git("reset", "--hard", base)
                write_json(entry / "source.json", {**original, **extra})
                published = self.commit("unsupported source layout")
                (entry / "README.md").write_text("Cannot infer whether this is a build input\n")
                head = self.commit("change unsupported source layout")
                with self.assertRaisesRegex(registry_ci.RegistryError, "published version changed or removed"):
                    registry_ci.plan(self.root, published, head, published=published)

    def test_published_module_cannot_be_removed(self) -> None:
        """Deleting its metadata as well does not hide a removed module."""
        entry = self.entry("alpha", "1.0.0")
        published = self.commit("main")
        shutil.rmtree(entry.parent)
        head = self.commit("remove module")
        with self.assertRaisesRegex(registry_ci.RegistryError, "published module cannot be deleted"):
            registry_ci.plan(self.root, published, head, published=published)

    def test_published_metadata_membership_cannot_be_removed(self) -> None:
        """A metadata-only edit cannot make an immutable release disappear."""
        entry = self.entry("alpha", "1.0.0")
        published = self.commit("main")
        write_json(entry.parent / "metadata.json", {"versions": []})
        head = self.commit("unlist published version")
        with self.assertRaisesRegex(registry_ci.RegistryError, "metadata and version directories differ"):
            registry_ci.plan(self.root, published, head, published=published)

    def test_unrelated_release_after_branch_fork_is_not_a_deletion(self) -> None:
        """A stale branch need not rebase for releases in an untouched module."""
        self.entry("alpha", "1.0.0")
        fork = self.commit("common ancestor")
        self.entry("beta", "1.0.0")
        published = self.commit("independent publication on main")
        self.git("checkout", "--detach", fork)
        self.entry("alpha", "2.0.0")
        head = self.commit("unrelated candidate")
        self.assertEqual(self.selected(fork, head, published), {("alpha", "2.0.0")})

    def test_newly_published_same_version_cannot_be_overwritten(self) -> None:
        """Fresh main catches a version collision even if the branch is stale."""
        self.entry("alpha", "1.0.0")
        fork = self.commit("common ancestor")
        entry = self.entry("alpha", "2.0.0")
        (entry / "MODULE.bazel").write_text('module(name = "alpha", version = "2.0.0")\n# Published\n')
        published = self.commit("publish candidate independently")
        self.git("checkout", "--detach", fork)
        entry = self.entry("alpha", "2.0.0")
        (entry / "MODULE.bazel").write_text('module(name = "alpha", version = "2.0.0")\n# Different\n')
        head = self.commit("colliding candidate")
        with self.assertRaisesRegex(registry_ci.RegistryError, "published version changed or removed"):
            registry_ci.plan(self.root, fork, head, published=published)

    def test_push_all_mode_checks_pre_push_publication_boundary(self) -> None:
        """Pushes must use event.before; the post-push main tree blesses itself."""
        entry = self.entry("alpha", "1.0.0")
        before = self.commit("pre-push main")
        (entry / "MODULE.bazel").write_text('module(name = "alpha", version = "1.0.0")\n# Edited\n')
        head = self.commit("push")
        with self.assertRaisesRegex(registry_ci.RegistryError, "published version changed or removed"):
            registry_ci.plan(self.root, None, head, all_versions=True, published=before, push=True)

    def test_non_fast_forward_push_cannot_roll_back_published_versions(self) -> None:
        """A rollback replaces main; it is not an unrelated stale PR branch."""
        self.entry("alpha", "1.0.0")
        old_head = self.commit("original main")
        self.entry("alpha", "2.0.0")
        before = self.commit("publish next release")
        self.git("checkout", "--detach", old_head)
        with self.assertRaisesRegex(registry_ci.RegistryError, "published version changed or removed"):
            registry_ci.plan(self.root, None, old_head, all_versions=True, published=before, push=True)

    def test_unknown_or_missing_publication_baseline_fails_closed(self) -> None:
        """No --all or missing-SHA fallback may bypass release-policy checks."""
        self.entry("alpha", "1.0.0")
        head = self.commit("registry")
        for published in (None, "main", "0" * 40):
            for all_versions in (False, True):
                with self.subTest(published=published, all_versions=all_versions):
                    with self.assertRaises((registry_ci.RegistryError, subprocess.CalledProcessError)):
                        registry_ci.plan(self.root, head, head, all_versions=all_versions, published=published)


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

    def test_runtime_preparation_requires_one_source_script_and_checksum(self) -> None:
        entry = self.entry("alpha", "1.0.0")
        path = entry / "presubmit.json"
        config = json.loads(path.read_text())
        valid = {"script": "tools/runtime/prepare.py", "sha256": "a" * 64}
        write_json(path, {**config, "test_runtime_preparation": valid})
        self.assertEqual(registry_ci.validate_entry(self.root, "alpha", "1.0.0")["test_runtime_preparation"], valid)
        with_mirrors = {**valid, "apt_mirror_protocol": "locked-runtime-v1"}
        write_json(path, {**config, "test_runtime_preparation": with_mirrors})
        self.assertEqual(registry_ci.validate_entry(self.root, "alpha", "1.0.0")["test_runtime_preparation"], with_mirrors)
        for invalid in (None, {}, {**valid, "args": ["--skip-tests"]},
                        {**valid, "apt_mirror_protocol": "unknown"}, {**valid, "apt_mirror_protocol": True},
                        {**valid, "sha256": "bad"}, {**valid, "script": "/tmp/prepare.py"},
                        {**valid, "script": "../prepare.py"}, {**valid, "script": "https://example.org/prepare.py"}):
            with self.subTest(invalid=invalid):
                write_json(path, {**config, "test_runtime_preparation": invalid})
                with self.assertRaises(registry_ci.RegistryError):
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

    def prepare(self, contents: str | None = None, expected_error: str | None = None,
                startup_args: list[str] | None = None, build_args: list[str] | None = None):
        work = self.root / "work"
        consumer = work / "consumer"
        artifacts = self.root / "artifacts"
        consumer.mkdir(parents=True, exist_ok=True)
        artifacts.mkdir(exist_ok=True)
        prefix = ["bazel", "--ignore_all_rc_files", f"--output_user_root={work / 'bazel'}",
                  *(startup_args or [])]

        def run(command, cwd, log):
            self.assertIn("--shared-only", command)
            self.assertIn("--bazel-arg=--registry=file:///registry", command)
            self.assertIn("--bazel-arg=--experimental_downloader_config=/registry/ci/source_mirrors.cfg", command)
            for flag in registry_ci.HTTP_DOWNLOAD_FLAGS:
                self.assertIn("--bazel-arg=" + flag, command)
            for flag in build_args or []:
                self.assertIn("--bazel-arg=" + flag, command)
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
                    registry_ci.prepare_rust(self.config, consumer, work, artifacts, prefix, [])
                execute.assert_not_called()
                return
            flags = registry_ci.prepare_rust(self.config, consumer, work, artifacts, prefix, [
                "--registry=file:///registry", "--platforms=@alpha//:platform", "--@alpha//:feature=True",
                "--experimental_downloader_config=/registry/ci/source_mirrors.cfg",
                *registry_ci.HTTP_DOWNLOAD_FLAGS,
                *(build_args or []),
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

    def test_shared_module_bazel_uses_the_same_startup_options(self) -> None:
        startup = ["--host_jvm_args=-Xmx2g", "--host_jvm_args=-Dexample=value with spaces"]
        _, execute, _ = self.prepare(startup_args=startup,
                                    build_args=["--jobs=1", "--discard_analysis_cache"])
        command = execute.call_args.args[0]
        self.assertEqual(command[command.index("--bazel") + 1], "bazel")
        self.assertEqual([arg.removeprefix("--bazel-startup-arg=") for arg in command
                          if arg.startswith("--bazel-startup-arg=")],
                         ["--ignore_all_rc_files", f"--output_user_root={self.root / 'work/bazel'}", *startup])
        self.assertFalse(any(arg.startswith("--bazel-arg=--host_jvm_args=") for arg in command))

    def test_helper_cannot_change_other_modules_or_runner_options(self) -> None:
        with self.assertRaisesRegex(registry_ci.RegistryError, "exactly its declared module"):
            self.prepare("common --override_module=other=/tmp/other\ncommon --remote_cache=https://invalid\n")

    def test_helper_cannot_redirect_outside_private_staging(self) -> None:
        with self.assertRaisesRegex(registry_ci.RegistryError, "private staging"):
            self.prepare("common --override_module=alpha=/tmp/other\n")


class IntegrationTestModuleTests(FixtureTestCase):
    """A separate test root must still exercise the reviewed registry recipe."""

    def setUp(self) -> None:
        super().setUp()
        self.registry_entry = self.entry("alpha", "1.0.0")
        self.config_path = self.registry_entry / "presubmit.json"
        self.config = json.loads(self.config_path.read_text())
        self.config.update({"integration_test_module": "tests/integration", "consumer_deps": []})
        self.directory = self.registry_entry / "tests/integration"
        self.directory.mkdir(parents=True)
        self.module = self.directory / "MODULE.bazel"
        self.module.write_text('module(name = "integration_tests")\n'
                               'bazel_dep(name = "alpha", version = "1.0.0")\n')
        (self.directory / "BUILD.bazel").write_text('filegroup(name = "archives", srcs = [])\n')

    def validate(self) -> dict:
        write_json(self.config_path, self.config)
        return registry_ci.validate_entry(self.root, "alpha", "1.0.0")

    def test_root_labels_require_an_explicit_integration_module(self) -> None:
        self.config["build_targets"].append("//:archives")
        self.config["test_targets"].append("//:archive_contract_test")
        self.validate()
        del self.config["integration_test_module"]
        with self.assertRaisesRegex(registry_ci.RegistryError, "explicit targets"):
            self.validate()

    def test_integration_root_does_not_allow_wildcards_or_unrelated_module_targets(self) -> None:
        for label in ("//...", "//:all", "//:all-targets", "@another//:test"):
            with self.subTest(label=label):
                self.config["test_targets"] = [label]
                with self.assertRaisesRegex(registry_ci.RegistryError, "explicit targets"):
                    self.validate()

    def test_test_module_cannot_escape_the_entry_or_use_symlinks(self) -> None:
        (self.registry_entry / "linked-tests").symlink_to(self.directory, target_is_directory=True)
        for name in ("../outside", "/tmp/tests", "tests/../integration", "linked-tests", "tests//integration"):
            with self.subTest(name=name):
                self.config["integration_test_module"] = name
                with self.assertRaises(registry_ci.RegistryError):
                    self.validate()
        self.config["integration_test_module"] = "tests/integration"
        (self.directory / "fixture.json").symlink_to(self.registry_entry / "source.json")
        with self.assertRaisesRegex(registry_ci.RegistryError, "regular files"):
            self.validate()

    def test_test_module_rejects_local_build_state_and_missing_build_file(self) -> None:
        for name in (".bazelrc", "MODULE.bazel.lock", "bazel-bin", "__pycache__", "test.pyc"):
            with self.subTest(name=name):
                path = self.directory / name
                path.write_text("local state")
                with self.assertRaisesRegex(registry_ci.RegistryError, "local build state"):
                    self.validate()
                path.unlink()
        (self.directory / "BUILD.bazel").unlink()
        with self.assertRaisesRegex(registry_ci.RegistryError, "Missing regular input"):
            self.validate()

    def test_test_module_cannot_override_registry_resolution_or_include_unchecked_files(self) -> None:
        original = self.module.read_text()
        for declaration in (
            'local_path_override(module_name = "alpha", path = "/tmp/alpha")',
            'single_version_override(module_name = "alpha", version = "1.0.0")',
            'include("//:other.MODULE.bazel")',
            'redirect = local_path_override\nredirect(module_name = "alpha", path = "/tmp/alpha")',
        ):
            with self.subTest(declaration=declaration):
                self.module.write_text(original + declaration + "\n")
                with self.assertRaisesRegex(registry_ci.RegistryError, "cannot include files or override"):
                    self.validate()

    def test_test_module_requires_the_exact_reviewed_dependency(self) -> None:
        for declaration in (
            'bazel_dep(name = "other", version = "1.0.0")',
            'bazel_dep(name = "alpha", version = "2.0.0")',
            'bazel_dep(name = "alpha", version = "1.0.0", repo_name = "alias")',
            'bazel_dep(name = "alpha", version = "1.0.0")\nbazel_dep(name = "alpha", version = "1.0.0")',
        ):
            with self.subTest(declaration=declaration):
                self.module.write_text(declaration + "\n")
                with self.assertRaisesRegex(registry_ci.RegistryError, "exact tested module"):
                    self.validate()

    def test_test_module_cannot_silently_ignore_generated_root_configuration(self) -> None:
        for field, value in (
            ("consumer_deps", [{"name": "platforms", "version": "1.0.0"}]),
            ("go_sdk", {"version": "1.25.0"}),
            ("rust_toolchain", {"version": "1.90.0"}),
            ("rust_preparation", {}),
        ):
            with self.subTest(field=field):
                config = copy.deepcopy(self.config)
                self.config[field] = value
                with self.assertRaisesRegex(registry_ci.RegistryError, "owns its dependencies"):
                    self.validate()
                self.config = config


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

    def test_root_integration_results_use_the_same_required_uncached_checks(self) -> None:
        for label in ("//:archive_contract_test", "@@//:archive_contract_test", "@//:archive_contract_test"):
            with self.subTest(label=label):
                events = self.events()
                for event in events:
                    for identifier in event["id"].values():
                        identifier["label"] = label
                self.verify(events, ["//:archive_contract_test"])
                events[0]["testResult"]["cachedLocally"] = True
                with self.assertRaises(registry_ci.RegistryError):
                    self.verify(events, ["//:archive_contract_test"])

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


class TestLogCollectionTests(FixtureTestCase):
    def test_failure_tail_starts_on_a_line_boundary_before_redaction(self):
        host = "build-private-mirror.example.invalid"
        suffix = host[len("build-"):] + "/archive/debian/package.deb\n"
        error = "last compiler error\n"
        following = "x" * (16000 - len(suffix) - len(error) - 1) + "\n" + error
        cases = [
            ("Downloading https://build-" + suffix + following, following),
            ("older line\n" + "x" * 15999 + "\n", "x" * 15999 + "\n"),
            (error, error),
            ("a" * 16001, ""),
        ]
        for original, expected in cases:
            log = self.root / "build.log"
            command = [sys.executable, "-c", "import sys; sys.stdout.write(sys.argv[1]); sys.exit(1)", original]
            with self.subTest(length=len(original)), mock.patch.object(sys, "stderr", io.StringIO()) as console:
                with self.assertRaises(registry_ci.RegistryError):
                    registry_ci.run_logged(command, self.root, log)
                self.assertEqual(console.getvalue(), expected + "\n")
                self.assertEqual(log.read_text(), original)

    def events(self) -> list[dict]:
        self.work = self.root / "work"
        self.bazel_out = self.work / "bazel/hash/execroot/_main/bazel-out"
        events = []
        for index, configuration in enumerate(("k8-fastbuild", "k8-fastbuild-ST-python")):
            directory = self.bazel_out / configuration / "testlogs" / "external/alpha+/test"
            directory.mkdir(parents=True)
            files = []
            for name in ("test.log", "test.xml"):
                source = directory / name
                source.write_text(f"{configuration}: {name}\n")
                files.append({"name": name, "uri": source.as_uri()})
            events.append({
                "id": {"testResult": {"label": "@@alpha+//:test", "configuration": {"id": configuration},
                                      "run": 1, "shard": 1, "attempt": index + 1}},
                "testResult": {"status": "FAILED" if index == 0 else "PASSED", "testActionOutput": files},
            })
        (self.work / "bazel-testlogs").symlink_to(self.bazel_out / "k8-fastbuild/testlogs")
        return events

    def collect(self, events: list[dict]) -> list[dict]:
        bep = self.root / "test-events.jsonl"
        bep.write_text("".join(json.dumps(event) + "\n" for event in events))
        artifacts = self.root / "artifacts"
        artifacts.mkdir(exist_ok=True)
        registry_ci.collect_test_logs(bep, self.work, artifacts)
        return json.loads((artifacts / "test-results.json").read_text())

    def test_transitioned_logs_and_retries_survive_outside_default_symlink(self) -> None:
        events = self.events()
        legacy_files = list((self.work / "bazel-testlogs").rglob("test.xml"))
        self.assertEqual(len(legacy_files), 1)
        index = self.collect(events)
        self.assertEqual([row["test"] for row in index], [event["id"]["testResult"] for event in events])
        self.assertEqual([row["status"] for row in index], ["FAILED", "PASSED"])
        paths = set()
        for row in index:
            self.assertEqual(len(row["files"]), 2)
            for record in row["files"]:
                paths.add(record["path"])
                data = (self.root / "artifacts" / record["path"]).read_bytes()
                self.assertIn(row["test"]["configuration"]["id"].encode(), data)
                self.assertEqual(record["sha256"], hashlib.sha256(data).hexdigest())
                self.assertEqual(record["size"], len(data))
        self.assertEqual(len(paths), 4)

    def test_missing_declared_log_is_rejected(self) -> None:
        events = self.events()
        (self.bazel_out / "k8-fastbuild/testlogs/external/alpha+/test/test.log").unlink()
        with self.assertRaisesRegex(registry_ci.RegistryError, "Missing test log"):
            self.collect(events)

    def test_nonlocal_and_escaping_logs_are_rejected(self) -> None:
        events = self.events()
        outside = self.root / "outside.log"
        outside.write_text("outside validation")
        consumer_file = self.work / "MODULE.bazel"
        consumer_file.write_text("not a test output")
        link = self.bazel_out / "k8-fastbuild/testlogs/outside.log"
        link.symlink_to(outside)
        for uri in ("https://example.invalid/test.log", outside.as_uri(), consumer_file.as_uri(), link.as_uri()):
            with self.subTest(uri=uri):
                events[0]["testResult"]["testActionOutput"][0]["uri"] = uri
                with self.assertRaises(registry_ci.RegistryError):
                    self.collect(events)

    def test_outputs_not_declared_as_logs_are_optional(self) -> None:
        events = self.events()
        events[0]["testResult"]["testActionOutput"].append({"name": "coverage.dat"})
        self.assertEqual(len(self.collect(events)[0]["files"]), 2)


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

    def collect(self, events: list[dict], **kwargs) -> dict:
        bep = self.root / "build-events.jsonl"
        bep.write_text("".join(json.dumps(event) + "\n" for event in events))
        artifacts = self.root / "artifacts"
        registry_ci.collect_outputs(bep, self.labels, self.work, artifacts, **kwargs)
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

    def expanded_tree_events(self) -> tuple[list[dict], Path, dict]:
        events = self.events()
        tree = self.work / "bazel-out/bin/tools"
        tree.mkdir(parents=True)
        (tree / "Text::Width").write_text("tree contents")
        # This sibling shares a lexical prefix with the directory. It must
        # remain an ordinary output and never be swallowed by tree grouping.
        sibling = tree.parent / "tools-extra.tar"
        sibling.write_bytes(b"ordinary tar bytes")
        (tree.parent / "not-exported").write_bytes(b"must not enter artifacts")
        events[0]["namedSetOfFiles"]["files"] = [
            {"name": path.relative_to(self.work).as_posix(), "uri": path.as_uri()}
            for path in [tree / "Text::Width", sibling]
        ]
        trees = {self.labels[0]: ["bazel-out/bin/tools"], self.labels[1]: []}
        return events, tree, trees

    def test_expanded_tree_records_use_declared_boundary_and_preserve_adjacent_file(self) -> None:
        events, tree, trees = self.expanded_tree_events()
        index = self.collect(events, declared_trees=trees, execution_root=self.work)
        records = index[self.labels[0]]
        self.assertEqual(len(records), 2)
        archive_record = next(item for item in records if item.get("type") == "tree_archive")
        regular_record = next(item for item in records if item.get("type") != "tree_archive")
        self.assertEqual(regular_record["path"], "outputs/bazel-out/bin/tools-extra.tar")
        self.assertEqual((self.root / "artifacts" / regular_record["path"]).read_bytes(), b"ordinary tar bytes")
        with tarfile.open(self.root / "artifacts" / archive_record["path"]) as archive:
            self.assertEqual(set(archive.getnames()), {"bazel-out/bin/tools", "bazel-out/bin/tools/Text::Width"})
        self.assertFalse(any(path.name == "Text::Width" for path in (self.root / "artifacts/outputs").rglob("*")))

    def test_expanded_tree_member_must_match_physical_execution_root_path(self) -> None:
        events, tree, trees = self.expanded_tree_events()
        events[0]["namedSetOfFiles"]["files"][0]["uri"] = (self.work / "runtime.tar").as_uri()
        with self.assertRaisesRegex(registry_ci.RegistryError, "does not match"):
            self.collect(events, declared_trees=trees, execution_root=self.work)

    def test_declared_empty_tree_survives_empty_bep_file_set(self) -> None:
        events, tree, trees = self.expanded_tree_events()
        (tree / "Text::Width").unlink()
        events[0]["namedSetOfFiles"]["files"] = []
        index = self.collect(events, declared_trees=trees, execution_root=self.work)
        with tarfile.open(self.root / "artifacts" / index[self.labels[0]][0]["path"]) as archive:
            self.assertEqual(archive.getnames(), ["bazel-out/bin/tools"])
            self.assertTrue(archive.getmembers()[0].isdir())

    def test_declared_directory_cannot_escape_execution_root(self) -> None:
        events, tree, trees = self.expanded_tree_events()
        trees[self.labels[0]] = ["bazel-out/../../tools"]
        with self.assertRaisesRegex(registry_ci.RegistryError, "Unsafe declared tree path"):
            self.collect(events, declared_trees=trees, execution_root=self.work)

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
        record = index[self.labels[0]][0]
        self.assertEqual(record["type"], "tree_archive")
        self.assertEqual(record["root"], "models")
        with tarfile.open(self.root / "artifacts" / record["path"]) as archive:
            self.assertEqual(archive.extractfile("models/model.yang").read(), b"module fixture {}")

    def test_repository_outputs_with_equal_basenames_keep_distinct_bytes(self) -> None:
        events = self.events()
        for offset, package in ((0, "libc6"), (2, "netbase")):
            output = self.work / "bazel" / "output-base" / "external" / package / "control.tar.xz"
            output.parent.mkdir(parents=True)
            output.write_bytes(package.encode())
            events[offset]["namedSetOfFiles"]["files"] = [
                {"name": output.name, "uri": output.as_uri()},
                {"name": output.name, "uri": output.as_uri()},
            ]
        index = self.collect(events)
        paths = []
        for label, package in zip(self.labels, ("libc6", "netbase")):
            self.assertEqual(len(index[label]), 1)
            record = index[label][0]
            paths.append(record["path"])
            self.assertEqual((self.root / "artifacts" / record["path"]).read_bytes(), package.encode())
            self.assertEqual(record["sha256"], hashlib.sha256(package.encode()).hexdigest())
        self.assertEqual(len(set(paths)), 2)

    def test_unprefixed_repository_output_cannot_escape_private_workspace(self) -> None:
        events = self.events()
        outside = self.root / "outside-control.tar.xz"
        outside.write_bytes(b"outside")
        link = self.work / "control.tar.xz"
        link.symlink_to(outside)
        events[0]["namedSetOfFiles"]["files"] = [{"name": link.name, "uri": link.as_uri()}]
        with self.assertRaisesRegex(registry_ci.RegistryError, "escapes work-dir"):
            self.collect(events)

    def test_tree_archive_preserves_posix_names_modes_links_and_empty_directories(self) -> None:
        events = self.events()
        tree = self.work / "tools"
        tree.mkdir()
        (tree / "empty").mkdir()
        for name in ("Text::CharWidth.3pm.gz", "xt_CONNMARK.h", "xt_connmark.h", "tool"):
            (tree / name).write_text(name)
        (tree / "tool").chmod(0o751)
        (tree / "alias").symlink_to("tool")
        events[0]["namedSetOfFiles"]["files"] = [{"name": "tools:POSIX", "uri": tree.as_uri()}]
        index = self.collect(events)
        record = index[self.labels[0]][0]
        archive_path = self.root / "artifacts" / record["path"]
        self.assertRegex(record["path"], r"^outputs/trees/[a-f0-9]{64}\.tar$")
        self.assertEqual(record["root"], "tools:POSIX")
        self.assertEqual(record["size"], archive_path.stat().st_size)
        digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
        self.assertEqual(record["sha256"], digest)
        with tarfile.open(archive_path) as archive:
            for name in ("Text::CharWidth.3pm.gz", "xt_CONNMARK.h", "xt_connmark.h"):
                self.assertEqual(archive.extractfile("tools:POSIX/" + name).read(), name.encode())
            self.assertEqual(archive.getmember("tools:POSIX/tool").mode, 0o751)
            self.assertTrue(archive.getmember("tools:POSIX/empty").isdir())
            link = archive.getmember("tools:POSIX/alias")
            self.assertTrue(link.issym())
            self.assertEqual(link.linkname, "tool")
            self.assertTrue(all(member.uid == member.gid == member.mtime == 0 for member in archive))
            archive.extractall(self.root / "restored", filter="data")
        restored = self.root / "restored/tools:POSIX"
        self.assertEqual((restored / "tool").stat().st_mode & 0o777, 0o751)
        self.assertEqual((restored / "alias").readlink(), Path("tool"))
        self.assertEqual((restored / "alias").read_text(), "tool")
        # Filesystem timestamps do not change the archive or output receipt.
        os.utime(tree / "tool", (1000, 1000))
        shutil.rmtree(self.root / "artifacts")
        self.assertEqual(self.collect(events)[self.labels[0]][0], record)

    def test_tree_links_cannot_escape_work_dir_or_cycle(self) -> None:
        events = self.events()
        tree = self.work / "tools"
        tree.mkdir()
        events[0]["namedSetOfFiles"]["files"] = [{"name": "tools", "uri": tree.as_uri()}]
        (self.root / "secret").write_text("not a build output")
        for target, message in ((self.root / "secret", "escapes work-dir"), (tree, "directory cycle")):
            with self.subTest(target=target):
                (tree / "link").symlink_to(target)
                with self.assertRaisesRegex(registry_ci.RegistryError, message):
                    self.collect(events)
                self.assertEqual(list((self.root / "artifacts/outputs/trees").iterdir()), [])
                (tree / "link").unlink()
                shutil.rmtree(self.root / "artifacts")

    def test_tree_links_to_other_declared_outputs_are_materialized(self) -> None:
        events = self.events()
        tree = self.work / "tools"
        tree.mkdir()
        (tree / "relative").symlink_to("../debug.tar")
        (tree / "absolute").symlink_to(self.work / "debug.tar")
        events[0]["namedSetOfFiles"]["files"] = [{"name": "tools", "uri": tree.as_uri()}]
        record = self.collect(events)[self.labels[0]][0]
        with tarfile.open(self.root / "artifacts" / record["path"]) as archive:
            for name in ("relative", "absolute"):
                self.assertTrue(archive.getmember("tools/" + name).isreg())
                self.assertEqual(archive.extractfile("tools/" + name).read(), b"debug")

    def test_tree_external_directory_backlink_survives_relocation(self) -> None:
        events = self.events()
        tree = self.work / "tools"
        shared = self.work / "shared"
        tree.mkdir()
        shared.mkdir()
        (tree / "payload").write_text("inside original tree")
        (tree / "imported").symlink_to("../shared")
        (shared / "backlink").symlink_to("../tools/payload")
        self.assertEqual((tree / "imported/backlink").read_text(), "inside original tree")
        events[0]["namedSetOfFiles"]["files"] = [{"name": "tools", "uri": tree.as_uri()}]
        record = self.collect(events)[self.labels[0]][0]
        with tarfile.open(self.root / "artifacts" / record["path"]) as archive:
            archive.extractall(self.root / "restored", filter="data")
        self.assertEqual(
            (self.root / "restored/tools/imported/backlink").read_text(), "inside original tree",
        )

    def test_tree_link_traversing_outside_then_back_is_self_contained(self) -> None:
        events = self.events()
        tree = self.work / "tools"
        shared = self.work / "shared"
        tree.mkdir()
        shared.mkdir()
        (tree / "payload").write_text("back inside")
        (shared / "backlink").symlink_to("../tools/payload")
        (tree / "link").symlink_to("../shared/backlink")
        self.assertEqual((tree / "link").read_text(), "back inside")
        events[0]["namedSetOfFiles"]["files"] = [{"name": "tools", "uri": tree.as_uri()}]
        record = self.collect(events)[self.labels[0]][0]
        with tarfile.open(self.root / "artifacts" / record["path"]) as archive:
            archive.extractall(self.root / "restored", filter="data")
        self.assertEqual((self.root / "restored/tools/link").read_text(), "back inside")

    def test_tree_nested_materialization_preserves_returned_subtree_contents(self) -> None:
        events = self.events()
        tree = self.work / "tools"
        shared = self.work / "shared"
        tree.mkdir()
        shared.mkdir()
        (tree / "inside").mkdir()
        (tree / "payload").write_text("nested contents")
        (tree / "inside/backlink").symlink_to("../payload")
        (tree / "imported").symlink_to("../shared")
        (shared / "nested").symlink_to("../tools/inside")
        self.assertEqual((tree / "imported/nested/backlink").read_text(), "nested contents")
        events[0]["namedSetOfFiles"]["files"] = [{"name": "tools", "uri": tree.as_uri()}]
        record = self.collect(events)[self.labels[0]][0]
        with tarfile.open(self.root / "artifacts" / record["path"]) as archive:
            archive.extractall(self.root / "restored", filter="data")
        restored = self.root / "restored/tools"
        self.assertEqual((restored / "imported/nested/backlink").read_text(), "nested contents")
        self.assertEqual((restored / "inside/backlink").readlink(), Path("../payload"))
        self.assertEqual((restored / "inside/backlink").read_text(), "nested contents")

    def test_tree_link_parent_after_symlink_keeps_physical_target(self) -> None:
        events = self.events()
        tree = self.work / "tools"
        shared = self.work / "shared"
        tree.mkdir()
        shared.mkdir()
        (tree / "tools").mkdir()
        (tree / "payload").write_text("physical target")
        (tree / "tools/payload").write_text("different lexical target")
        (tree / "dir").symlink_to("../shared")
        (tree / "link").symlink_to("dir/../tools/payload")
        self.assertEqual((tree / "link").read_text(), "physical target")
        events[0]["namedSetOfFiles"]["files"] = [{"name": "tools", "uri": tree.as_uri()}]
        record = self.collect(events)[self.labels[0]][0]
        with tarfile.open(self.root / "artifacts" / record["path"]) as archive:
            archive.extractall(self.root / "restored", filter="data")
        self.assertEqual((self.root / "restored/tools/link").read_text(), "physical target")

    def test_tree_link_leaving_and_reentering_renamed_root_is_portable(self) -> None:
        events = self.events()
        tree = self.work / "tools"
        tree.mkdir()
        (tree / "payload").write_text("renamed root contents")
        (tree / "link").symlink_to("../tools/payload")
        self.assertEqual((tree / "link").read_text(), "renamed root contents")
        events[0]["namedSetOfFiles"]["files"] = [{"name": "renamed-tools", "uri": tree.as_uri()}]
        record = self.collect(events)[self.labels[0]][0]
        with tarfile.open(self.root / "artifacts" / record["path"]) as archive:
            archive.extractall(self.root / "restored", filter="data")
        self.assertEqual(
            (self.root / "restored/renamed-tools/link").read_text(), "renamed root contents",
        )

    def test_conflicting_trees_are_rejected(self) -> None:
        events = self.events()
        for position, name in ((0, "first"), (2, "second")):
            tree = self.work / name
            tree.mkdir()
            (tree / "file").write_text(name)
            events[position]["namedSetOfFiles"]["files"] = [{"name": "tree", "uri": tree.as_uri()}]
        with self.assertRaisesRegex(registry_ci.RegistryError, "Conflicting"):

            self.collect(events)

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


class NativeValidationTests(unittest.TestCase):
    def test_wrong_userspace_is_rejected_even_on_matching_host(self) -> None:
        with mock.patch.object(registry_ci.platform, "system", return_value="Linux"), \
             mock.patch.object(registry_ci.platform, "machine", return_value="x86_64"), \
             mock.patch.object(registry_ci.subprocess, "check_output", return_value="arm64\n"):
            with self.assertRaisesRegex(registry_ci.RegistryError, "userspace"):
                registry_ci.verify_native("amd64")

    def test_foreign_host_is_rejected_even_with_matching_userspace(self) -> None:
        with mock.patch.object(registry_ci.platform, "system", return_value="Linux"), \
             mock.patch.object(registry_ci.platform, "machine", return_value="x86_64"), \
             mock.patch.object(registry_ci.subprocess, "check_output", return_value="arm64\n"):
            with self.assertRaisesRegex(registry_ci.RegistryError, "native Linux host"):
                registry_ci.verify_native("arm64")


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


class StagedCrossRoutingTests(FixtureTestCase):
    def setUp(self):
        super().setUp()
        for version in ("1.0.0", "2.0.0"):
            entry = self.entry("alpha", version)
            config = json.loads((entry / "presubmit.json").read_text())
            config["architectures"].append("arm64")
            config["platforms"]["arm64"] = "@platforms//host:host"
            write_json(entry / "presubmit.json", config)
        self.entry("beta", "1.0.0")
        self.head = self.commit("published contracts")

    def planned(self, routes, all_versions=True, cross_all=False):
        with mock.patch.object(registry_ci, "ARM_CROSS_VERSIONS", routes), \
                mock.patch.object(registry_ci, "ARM_CROSS_ALL", cross_all):
            return registry_ci.plan(self.root, None, self.head, all_versions=all_versions,
                                    latest_versions=not all_versions, published=self.head)["include"]

    def test_survey_cross_builds_every_arm_version_without_changing_native_jobs(self):
        before = {str(path): path.read_bytes() for path in (self.root / "modules").rglob("*") if path.is_file()}
        native = self.planned({})
        survey = self.planned({}, cross_all=True)
        self.assertEqual(len(survey), len(native))
        for original, routed in zip(native, survey):
            if original["architecture"] == "arm64":
                self.assertEqual(routed, {**original, "execution_architecture": "amd64",
                                         "cross_compile": True, "runner": registry_ci.RUNNERS["amd64"]})
            else:
                self.assertEqual(routed, original)
        self.assertEqual([job["version"] for job in survey if job["cross_compile"]], ["1.0.0", "2.0.0"])
        self.assertEqual(before, {str(path): path.read_bytes() for path in (self.root / "modules").rglob("*") if path.is_file()})

    def test_survey_rejects_non_boolean_selection(self):
        for value in (None, "true", 1, []):
            with self.subTest(value=value), self.assertRaises(registry_ci.RegistryError):
                self.planned({}, cross_all=value)

    def test_empty_routes_preserve_every_native_job_and_original_contract(self):
        jobs = self.planned({})
        self.assertEqual(len(jobs), 5)
        self.assertTrue(all(not job["cross_compile"] for job in jobs))
        for job in jobs:
            self.assertEqual(job["execution_architecture"], job["architecture"])
            self.assertEqual(job["runner"], registry_ci.RUNNERS[job["architecture"]])

    def test_staged_default_keeps_unlisted_versions_on_native_arm(self):
        self.assertIs(registry_ci.ARM_CROSS_ALL, False)
        jobs = registry_ci.plan(self.root, None, self.head, all_versions=True,
                                published=self.head)["include"]
        self.assertEqual(jobs, self.planned({}))

    def test_exact_version_moves_only_declared_arm_row_without_mutating_inputs(self):
        before = {str(path): path.read_bytes() for path in (self.root / "modules").rglob("*") if path.is_file()}
        native = self.planned({})
        routed = self.planned({"alpha": ("1.0.0",), "beta": ("1.0.0",)})
        identity = lambda job: (job["module"], job["version"], job["architecture"])
        self.assertCountEqual([identity(job) for job in native], [identity(job) for job in routed])
        moved = [job for job in routed if job["cross_compile"]]
        self.assertEqual([identity(job) for job in moved], [("alpha", "1.0.0", "arm64")])
        self.assertEqual(moved[0]["execution_architecture"], "amd64")
        self.assertEqual(moved[0]["runner"], registry_ci.RUNNERS["amd64"])
        self.assertEqual([job for job in routed if not job["cross_compile"]],
                         [job for job in native if identity(job) != identity(moved[0])])
        self.assertEqual(before, {str(path): path.read_bytes() for path in (self.root / "modules").rglob("*") if path.is_file()})
        self.assertFalse(any(job["cross_compile"] for job in self.planned({"alpha": ("1.0.0",)}, all_versions=False)))

    def test_changed_published_source_is_still_rejected_with_cross_route(self):
        path = self.root / "modules/alpha/1.0.0/MODULE.bazel"
        path.write_text(path.read_text() + "# changed published input\n")
        changed = self.commit("illegal published source edit")
        with mock.patch.object(registry_ci, "ARM_CROSS_VERSIONS", {"alpha": ("1.0.0",)}), \
                self.assertRaises(registry_ci.RegistryError):
            registry_ci.plan(self.root, self.head, changed, published=self.head)

    def test_malformed_temporary_routes_fail_instead_of_silently_changing_mode(self):
        for routes in ([], {"alpha": "1.0.0"}, {"alpha": ()}, {"bad/name": ("1.0.0",)},
                       {"alpha": ("../version",)}, {"alpha": ("1.0.0", "1.0.0")}):
            with self.subTest(routes=routes), self.assertRaises(registry_ci.RegistryError):
                self.planned(routes)


class WorkflowMatrixTests(unittest.TestCase):
    def setUp(self):
        self.workflow = (registry_ci.ROOT / ".github/workflows/registry-ci.yml").read_text()

    def test_split_plan_preserves_native_and_cross_jobs_and_marks_empty_groups(self):
        script = self.workflow.split("          python3 - <<'PY'\n", 1)[1].split("\n          PY", 1)[0]
        script = "\n".join(line[10:] for line in script.splitlines())
        amd = {"module": "alpha", "version": "1.0.0", "architecture": "amd64",
               "execution_architecture": "amd64", "cross_compile": False,
               "runner": registry_ci.RUNNERS["amd64"]}
        arm = {**amd, "architecture": "arm64", "execution_architecture": "arm64", "runner": registry_ci.RUNNERS["arm64"]}
        second_amd = {**amd, "module": "beta"}
        cross = {**second_amd, "architecture": "arm64", "cross_compile": True}
        for jobs, succeeds in (([], True), ([amd], True), ([arm], True),
                               ([arm, amd, second_amd, cross], True), ([cross], True),
                               ([{**arm, "architecture": "armhf"}], False),
                               ([{**arm, "cross_compile": True}], False),
                               ([{**cross, "cross_compile": "true"}], False),
                               ([{**cross, "runner": registry_ci.RUNNERS["arm64"]}], False),
                               ([{**amd, "cross_compile": True}], False), ([arm, arm], False)):
            with self.subTest(jobs=jobs), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                matrix = {"include": jobs}
                (root / "plan.json").write_text(json.dumps(matrix))
                output = root / "outputs"
                result = subprocess.run([sys.executable, "-I", "-S", "-c", script], cwd=root,
                    env={**os.environ, "EVENT_NAME": "workflow_dispatch", "GITHUB_OUTPUT": str(output)},
                    text=True, capture_output=True)
                if not succeeds:
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("validation", result.stderr)
                    self.assertFalse(output.exists())
                    continue
                self.assertEqual(result.returncode, 0, result.stderr)
                values = dict(line.split("=", 1) for line in output.read_text().splitlines())
                self.assertEqual(json.loads(values["matrix"]), matrix)
                self.assertEqual(values["has_jobs"], str(bool(jobs)).lower())
                selected = []
                for group, execution in (("local", "amd64"), ("hosted_arm", "arm64")):
                    expected = [job for job in jobs if job["execution_architecture"] == execution]
                    actual = json.loads(values[group + "_matrix"])["include"]
                    self.assertEqual(actual, expected)
                    self.assertEqual(values["has_" + group + "_jobs"], str(bool(expected)).lower())
                    selected.extend(actual)
                self.assertCountEqual(selected, jobs)

    def test_one_local_budget_and_separate_hosted_admission_share_validation_body(self):
        for architecture in ("local", "hosted_arm"):
            # A job block ends at the next two-space job key, not a nested field.
            block = re.search(r"^  modules_" + architecture + r":\n(.*?)(?=^  \w+:|\Z)",
                              self.workflow, re.MULTILINE | re.DOTALL)[1]
            self.assertIn("needs: plan", block)
            if architecture == "local":
                self.assertIn("if: ${{ always() && !cancelled() && needs.plan.result == 'success' && "
                              "needs.plan.outputs.has_local_jobs == 'true' }}", block)
            else:
                self.assertIn("if: needs.plan.outputs.has_hosted_arm_jobs == 'true'", block)
            self.assertIn("matrix: ${{ fromJSON(needs.plan.outputs." + architecture + "_matrix) }}", block)
            self.assertIn("uses: ./.github/workflows/registry-module.yml", block)
            for name in ("module", "version", "architecture", "execution_architecture", "cross_compile"):
                self.assertIn(name + ": ${{ matrix." + name + " }}", block)
            self.assertIn("runner: ${{ toJSON(matrix.runner) }}", block)
            self.assertEqual("max-parallel: 10" in block, architecture == "local")
            self.assertNotIn("steps:", block)
        shared = (registry_ci.ROOT / ".github/workflows/registry-module.yml").read_text()
        self.assertIn("workflow_call:", shared)
        self.assertIn("runs-on: ${{ fromJSON(inputs.runner) }}", shared)
        self.assertEqual(shared.count("name: Build and test through the registry"), 1)
        self.assertNotIn("name: Build and test through the registry", self.workflow)
        self.assertIn("needs: [plan, unit, cross_fixture, modules_local, modules_hosted_arm]", self.workflow)

    def test_aggregate_requires_cross_fixture_and_only_explicitly_empty_module_groups(self):
        block = self.workflow.split("  required:\n", 1)[1]
        script = block.split("        run: |\n", 1)[1]
        script = "\n".join(line[10:] for line in script.splitlines())
        for architecture in ("local", "hosted_arm"):
            self.assertIn(architecture.upper() + "_RESULT: ${{ needs.modules_" + architecture + ".result }}", block)
            self.assertIn("HAS_" + architecture.upper() + "_JOBS: ${{ needs.plan.outputs.has_" + architecture + "_jobs }}", block)
        base = {"PLAN_RESULT": "success", "UNIT_RESULT": "success", "CROSS_FIXTURE_RESULT": "success", "LOCAL_RESULT": "success",
                "HOSTED_ARM_RESULT": "success", "HAS_LOCAL_JOBS": "true", "HAS_HOSTED_ARM_JOBS": "true"}
        cases = [(base, True)]
        for architecture in ("LOCAL", "HOSTED_ARM"):
            flag, result = "HAS_" + architecture + "_JOBS", architecture + "_RESULT"
            cases.append(({**base, flag: "false", result: "skipped"}, True))
            for invalid in ("failure", "cancelled", "skipped", ""):
                cases.append(({**base, result: invalid}, False))
            cases.append(({**base, flag: "false"}, False))
            cases.append(({**base, flag: "", result: "skipped"}, False))
        cases.append(({**base, "HAS_LOCAL_JOBS": "false", "HAS_HOSTED_ARM_JOBS": "false",
                       "LOCAL_RESULT": "skipped", "HOSTED_ARM_RESULT": "skipped"}, True))
        self.assertIn("CROSS_FIXTURE_RESULT: ${{ needs.cross_fixture.result }}", block)
        for prerequisite in ("PLAN_RESULT", "UNIT_RESULT", "CROSS_FIXTURE_RESULT"):
            for invalid in ("failure", "cancelled", "skipped", ""):
                cases.append(({**base, prerequisite: invalid}, False))
        for environment, succeeds in cases:
            with self.subTest(environment=environment):
                result = subprocess.run(["/bin/bash", "-c", script], env={**os.environ, **environment},
                                        text=True, capture_output=True)
                self.assertEqual(result.returncode == 0, succeeds, result.stderr)


    def test_native_and_cross_jobs_run_distinct_explicit_suites(self):
        unit = self.workflow.split("  unit:\n", 1)[1].split("  cross_fixture:\n", 1)[0]
        cross = self.workflow.split("  cross_fixture:\n", 1)[1].split("  modules_local:\n", 1)[0]
        self.assertIn("python3 ci/run_runner_tests.py --suite native", unit)
        self.assertIn("architecture: amd64", unit)
        self.assertIn("architecture: arm64", unit)
        self.assertIn("runner: [ubuntu-24.04-arm]", unit)
        self.assertIn("timeout-minutes: ${{ matrix.timeout_minutes }}", unit)
        rows = re.findall(r"- architecture: (\w+)\n\s+timeout_minutes: (\d+)\n\s+runner: \[([^\]]+)\]\n"
                          r"\s+machine: (\w+)\n\s+bazel_arch: (\w+)\n\s+bazel_sha: ([0-9a-f]+)", unit)
        self.assertEqual(rows, [
            ("amd64", "45", "self-hosted, Linux, X64, debian-trixie-container", "x86_64", "x86_64",
             "61d89402f0368e64b6c827be5de79d8e65382e8124c3cbb97325611a1851392e"),
            ("arm64", "30", "ubuntu-24.04-arm", "aarch64", "arm64",
             "b7f2a85595e8a87d54843bc656c1e379fd9b8c1b5f783dc41717c1d7eb7cc49f"),
        ])
        self.assertNotIn("REGISTRY_CI_TEST_ARM_EXECUTOR", unit)
        self.assertIn("python3 ci/run_runner_tests.py --suite cross", cross)
        self.assertIn("REGISTRY_CI_TEST_BAZEL: /usr/local/bin/bazel", cross)
        self.assertIn("REGISTRY_CI_TEST_ARM_EXECUTOR: /usr/local/bin/sonic-arm64", cross)
        self.assertIn("[[ -x \"$REGISTRY_CI_TEST_BAZEL\" && -x \"$REGISTRY_CI_TEST_ARM_EXECUTOR\" ]]", cross)
        self.assertIn("timeout-minutes: 60", cross)
        self.assertIn("name: registry-ci-arm-cross-fixture", cross)
        # Only the optional audit-artifact transfer may continue on error. The
        # source/compiler/runtime suite and the containing job remain required.
        self.assertNotIn("continue-on-error", cross.split("    steps:\n", 1)[0])
        suite = cross.split("      - name: Test the cross compiler and ARM runtime\n", 1)[1].split("      - ", 1)[0]
        self.assertNotIn("continue-on-error", suite)
        for block in (unit, cross):
            self.assertIn("needs: plan", block)
            self.assertIn("if: ${{ always() && !cancelled() }}", block)

    def test_native_unit_bazel_setup_uses_each_execution_architecture(self):
        unit = self.workflow.split("  unit:\n", 1)[1].split("  cross_fixture:\n", 1)[0]
        script = TestContainerTests.step(unit, "Install Bazel for real runner integration tests")
        rows = re.findall(r"- architecture: (\w+)\n\s+runner: \[[^\]]+\]\n"
                          r"\s+machine: (\w+)\n\s+bazel_arch: (\w+)\n\s+bazel_sha: ([0-9a-f]+)", unit)
        for architecture, machine, bazel_arch, checksum in rows:
            with self.subTest(architecture=architecture), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                environment = TestContainerTests.shell_environment(self, root, architecture, architecture, False)
                environment.update(EXPECTED_MACHINE=machine, BAZEL_ARCH=bazel_arch, BAZEL_SHA=checksum,
                                   GITHUB_ENV=str(root / "github-env"))
                chmod = root / "bin/chmod"
                chmod.write_text('#!/bin/bash\nprintf "%s\\n" "$@" > "$RUNNER_TEMP/chmod-args"\n')
                chmod.chmod(0o755)
                result = subprocess.run(["/bin/bash", "-c", script], env=environment,
                                        text=True, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual((root / "CHECKSUM_ARGS").read_text().splitlines(), ["--check", "--strict"])
                binary = "/usr/local/lib/bazel-8.5.1" if architecture == "amd64" else environment["RUNNER_TEMP"] + "/bazel-8.5.1"
                self.assertEqual((root / "CHECKSUM_LOG").read_text().strip(), checksum + "  " + binary)
                selected = "/usr/local/bin/bazel" if architecture == "amd64" else binary
                self.assertEqual((root / "github-env").read_text(), "REGISTRY_CI_TEST_BAZEL=" + selected + "\n")
                if architecture == "amd64":
                    self.assertFalse((root / "CURL_LOG").exists())
                else:
                    self.assertEqual((root / "CURL_LOG").read_text().splitlines(),
                                     ["--fail", "--location", "--retry", "3", "--output", binary,
                                      "https://releases.bazel.build/8.5.1/release/bazel-8.5.1-linux-arm64"])
                    self.assertEqual((Path(environment["RUNNER_TEMP"]) / "chmod-args").read_text().splitlines(), ["0755", binary])
                bad = subprocess.run(["/bin/bash", "-c", script],
                                     env={**environment, "NATIVE_MACHINE": "unexpected"}, text=True, capture_output=True)
                self.assertNotEqual(bad.returncode, 0)


class TestContainerTests(unittest.TestCase):
    def test_runtime_setup_requires_root_container_trixie_and_pinned_image(self):
        image = "debian:trixie@sha256:" + "b" * 64
        for uid, container, release, selected, succeeds in (
                (0, True, "VERSION_CODENAME=trixie\n", image, True),
                (1000, True, "VERSION_CODENAME=trixie\n", image, False),
                (0, False, "VERSION_CODENAME=trixie\n", image, False),
                (0, True, "VERSION_CODENAME=bookworm\n", image, False),
                (0, True, "VERSION_CODENAME=trixie\n", "debian:trixie", False)):
            with self.subTest(uid=uid, container=container, release=release, selected=selected), \
                    mock.patch.object(registry_ci.os, "geteuid", return_value=uid), \
                    mock.patch.object(Path, "exists", return_value=container), \
                    mock.patch.object(Path, "read_text", return_value=release):
                if succeeds:
                    registry_ci.require_test_container(selected)
                else:
                    with self.assertRaises(registry_ci.RegistryError):
                        registry_ci.require_test_container(selected)

    @staticmethod
    def step(workflow, name):
        block = workflow.split("      - name: " + name + "\n", 1)[1].split("\n      - ", 1)[0]
        return "\n".join(line[10:] for line in block.split("        run: |\n", 1)[1].splitlines())

    def shell_environment(self, root, architecture, execution, cross):
        commands = root / "bin"
        commands.mkdir()
        for name, body in {
            "sudo": ('printf "%s\\n" "$*" >> "$SUDO_LOG"\n[[ "$1" == -n ]]\nshift\n'
                     'if [[ "$1" == --preserve-env=DEBIAN_MIRROR_ROOT,DEBIAN_SECURITY_MIRROR_ROOT,DEBIAN_MIRROR_BASE_URL,DEBIAN_SECURITY_MIRROR_BASE_URL,GITHUB_ACTIONS ]]; then shift; fi\n'
                     'exec "$@"\n'),
            "git": 'printf "%s\\n" "$@" > "$GIT_LOG"\n',
            "python3": 'printf "%s\\n" "$@" > "$CAPTURE"\n',
            "uname": '[[ "$1" == -m ]]\nprintf "%s\\n" "$NATIVE_MACHINE"\n',
            "sha256sum": 'cat > "$CHECKSUM_LOG"\nprintf "%s\\n" "$@" > "$CHECKSUM_ARGS"\n',
            "curl": 'printf "%s\\n" "$@" > "$CURL_LOG"\n',
            "install": 'printf "%s\\n" "$@" > "$INSTALL_LOG"\n',
            "chown": 'printf "%s\\n" "$@" > "$CHOWN_LOG"\n',
        }.items():
            command = commands / name
            command.write_text("#!/bin/bash\nset -euo pipefail\n" + body)
            command.chmod(0o755)
        executor = root / "ARM executor"
        executor.write_text("#!/bin/sh\nexit 99\n")
        executor.chmod(0o755)
        (root / "workspace/ci-artifacts").mkdir(parents=True)
        (root / "runner temp").mkdir()
        environment = {**os.environ, "PATH": str(commands) + os.pathsep + os.environ["PATH"],
                       "CI_MODULE": "alpha", "CI_VERSION": "1.0.0", "CI_ARCHITECTURE": architecture,
                       "CI_EXECUTION_ARCHITECTURE": execution, "CI_CROSS_COMPILE": str(cross).lower(),
                       "NATIVE_MACHINE": "x86_64" if execution == "amd64" else "aarch64",
                       "SONIC_RUNNER_IMAGE_REFERENCE": "sonic-slave-runner@sha256:" + "c" * 64,
                       "ARM_TEST_EXECUTOR": str(executor), "TEST_CONTAINER_IMAGE": "unused",
                       "GITHUB_WORKSPACE": str(root / "workspace"), "RUNNER_TEMP": str(root / "runner temp")}
        for variable in ("CAPTURE", "SUDO_LOG", "GIT_LOG", "CHECKSUM_LOG", "CHECKSUM_ARGS", "CURL_LOG",
                         "INSTALL_LOG", "CHOWN_LOG"):
            environment[variable] = str(root / variable)
        return environment

    def test_workflow_passes_native_and_cross_execution_inputs_without_changing_target(self):
        workflow = (registry_ci.ROOT / ".github/workflows/registry-module.yml").read_text()
        expression = next(line.split("container: ", 1)[1] for line in workflow.splitlines()
                          if line.strip().startswith("container: "))
        selection = re.fullmatch(
            r"\$\{\{ inputs\.architecture == 'arm64' && !inputs\.cross_compile && '(\S+@sha256:[0-9a-f]{64})' \|\| '' \}\}",
            expression)
        self.assertIsNotNone(selection)
        self.assertIn("TEST_CONTAINER_IMAGE: " + expression, workflow)
        self.assertIn("if: inputs.architecture == 'arm64' && !inputs.cross_compile", workflow)
        self.assertIn("CI_EXECUTION_ARCHITECTURE: ${{ inputs.execution_architecture || inputs.architecture }}", workflow)
        self.assertRegex(workflow, r"cross_compile:\n\s+type: boolean\n\s+default: false")
        for architecture, execution, cross in (("amd64", "amd64", False), ("arm64", "arm64", False),
                                                ("arm64", "amd64", True)):
            with self.subTest(architecture=architecture, cross=cross), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                environment = self.shell_environment(root, architecture, execution, cross)
                environment["TEST_CONTAINER_IMAGE"] = selection[1] if execution == "arm64" else ""
                for name in ("Validate execution route", "Install Bazel 8.5.1", "Build and test through the registry"):
                    result = subprocess.run(["/bin/bash", "-c", self.step(workflow, name)], env=environment,
                                            text=True, capture_output=True)
                    self.assertEqual(result.returncode, 0, result.stderr)
                checksum = (root / "CHECKSUM_LOG").read_text().split()
                self.assertEqual((root / "CHECKSUM_ARGS").read_text().splitlines(), ["--check", "--strict"])
                if execution == "amd64":
                    self.assertEqual(checksum, ["61d89402f0368e64b6c827be5de79d8e65382e8124c3cbb97325611a1851392e",
                                                "/usr/local/lib/bazel-8.5.1"])
                    self.assertFalse((root / "CURL_LOG").exists())
                    self.assertFalse((root / "INSTALL_LOG").exists())
                else:
                    self.assertEqual(checksum, ["b7f2a85595e8a87d54843bc656c1e379fd9b8c1b5f783dc41717c1d7eb7cc49f",
                                                "/tmp/bazel"])
                    self.assertIn("https://releases.bazel.build/8.5.1/release/bazel-8.5.1-linux-arm64",
                                  (root / "CURL_LOG").read_text().splitlines())
                    self.assertEqual((root / "INSTALL_LOG").read_text().splitlines(),
                                     ["-m", "0755", "/tmp/bazel", "/usr/local/bin/bazel"])
                arguments = (root / "CAPTURE").read_text().splitlines()
                self.assertEqual(arguments[arguments.index("--architecture") + 1], architecture)
                self.assertEqual(arguments[arguments.index("--test-container-image") + 1],
                                 environment["SONIC_RUNNER_IMAGE_REFERENCE"] if execution == "amd64" else selection[1])
                self.assertEqual(arguments[arguments.index("--bazel") + 1], "/usr/local/bin/bazel")
                self.assertEqual([arg for arg in arguments if arg.startswith("--bazel-startup-arg=")],
                                 ["--bazel-startup-arg=--host_jvm_args=-Xmx2g"] if execution == "amd64" else [])
                self.assertEqual([arg for arg in arguments if arg.startswith("--bazel-build-arg=")],
                                 ["--bazel-build-arg=--jobs=1", "--bazel-build-arg=--discard_analysis_cache"]
                                 if execution == "amd64" else [])
                self.assertEqual("--cross-compile" in arguments, cross)
                self.assertEqual("--test-executor" in arguments, cross)
                if cross:
                    self.assertEqual(arguments[arguments.index("--test-executor") + 1], environment["ARM_TEST_EXECUTOR"])
                self.assertEqual(arguments[arguments.index("--work-dir") + 1], str(root / "runner temp/registry-ci"))
                if execution == "amd64":
                    self.assertEqual((root / "GIT_LOG").read_text().splitlines(),
                                     ["config", "--global", "--add", "safe.directory", str(root / "workspace")])
                    self.assertEqual(len((root / "SUDO_LOG").read_text().splitlines()), 2)
                else:
                    self.assertFalse((root / "SUDO_LOG").exists())

    def test_invalid_or_unprepared_routes_fail_before_invoking_the_helper(self):
        workflow = (registry_ci.ROOT / ".github/workflows/registry-module.yml").read_text()
        script = self.step(workflow, "Validate execution route") + "\n" + self.step(workflow, "Build and test through the registry")
        cases = [("amd64", "amd64", True, {}), ("arm64", "arm64", True, {}),
                 ("arm64", "amd64", False, {}), ("armhf", "arm64", False, {}),
                 ("arm64", "amd64", True, {"NATIVE_MACHINE": "aarch64"}),
                 ("arm64", "amd64", True, {"ARM_TEST_EXECUTOR": "/absent/executor"}),
                 ("arm64", "amd64", True, {"CI_CROSS_COMPILE": "maybe"}),
                 ("arm64", "amd64", True, {"SONIC_RUNNER_IMAGE_REFERENCE": ""}),
                 ("amd64", "amd64", False, {"SONIC_RUNNER_IMAGE_REFERENCE": ""})]
        for architecture, execution, cross, overrides in cases:
            with self.subTest(route=(architecture, execution, cross), overrides=overrides), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                environment = {**self.shell_environment(root, architecture, execution, cross), **overrides}
                result = subprocess.run(["/bin/bash", "-c", script], env=environment, text=True, capture_output=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse((root / "CAPTURE").exists())

    def test_local_p4_builds_limit_make_for_targets_and_tools(self):
        workflow = (registry_ci.ROOT / ".github/workflows/registry-module.yml").read_text()
        script = self.step(workflow, "Build and test through the registry")
        for module, target, execution, prior, expected in (
            ("p4c", "amd64", "amd64", None, "--eval=.NOTPARALLEL:"),
            ("p4c", "arm64", "amd64", "-r --warn-undefined-variables", "-r --warn-undefined-variables --eval=.NOTPARALLEL:"),
            ("p4lang-bmv2", "amd64", "amd64", "", "--eval=.NOTPARALLEL:"),
            ("sonic-dash", "arm64", "amd64", "-r", "-r --eval=.NOTPARALLEL:"),
            ("p4c", "arm64", "arm64", "-r", None),
            ("libyang", "amd64", "amd64", "-r", None),
        ):
            with self.subTest(module=module, target=target, execution=execution), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                env = self.shell_environment(root, target, execution, target != execution)
                env["CI_MODULE"] = module
                env.pop("GNUMAKEFLAGS", None)
                if prior is not None:
                    env["GNUMAKEFLAGS"] = prior
                result = subprocess.run(["bash", "-c", script], env=env, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                args = (root / "CAPTURE").read_text().splitlines()
                self.assertEqual([arg for arg in args if "GNUMAKEFLAGS=" in arg], [] if expected is None else [
                    "--bazel-build-arg=--action_env=GNUMAKEFLAGS=" + expected,
                    "--bazel-build-arg=--host_action_env=GNUMAKEFLAGS=" + expected,
                ])

    def test_module_archive_preserves_modes_and_uses_sudo_only_for_local_execution(self):
        workflow = (registry_ci.ROOT / ".github/workflows/registry-module.yml").read_text()
        script = self.step(workflow, "Archive module validation results")
        for architecture, execution, cross in (("amd64", "amd64", False), ("arm64", "arm64", False),
                                                ("arm64", "amd64", True)):
            with self.subTest(architecture=architecture, cross=cross), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                environment = self.shell_environment(root, architecture, execution, cross)
                payload = root / "workspace/ci-artifacts/payload"
                payload.write_bytes(b"retained evidence\n")
                payload.chmod(0o751)
                result = subprocess.run(["/bin/bash", "-c", script], cwd=registry_ci.ROOT,
                                        env=environment, text=True, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual((root / "CAPTURE").read_text().splitlines(),
                                 ["ci/private_mirrors.py", "check-artifacts", "--artifacts",
                                  str(root / "workspace/ci-artifacts")])
                archive = root / "runner temp/registry-ci-evidence.tar"
                with tarfile.open(archive) as transport:
                    member = transport.getmember("./payload")
                    self.assertEqual(member.mode, 0o751)
                    self.assertEqual(transport.extractfile(member).read(), b"retained evidence\n")
                if execution == "amd64":
                    self.assertEqual(len((root / "SUDO_LOG").read_text().splitlines()), 3)
                    self.assertEqual((root / "CHOWN_LOG").read_text().splitlines(),
                                     [f"{os.getuid()}:{os.getgid()}", str(archive)])
                else:
                    self.assertFalse((root / "SUDO_LOG").exists())
                    self.assertFalse((root / "CHOWN_LOG").exists())


class BazelStartupArgumentTests(unittest.TestCase):
    def test_cli_forwards_repeated_startup_options_and_preserves_the_default(self) -> None:
        for startup, build in (([], []),
                               (["--host_jvm_args=-Xmx2g", "--host_jvm_args=-Dexample=value with spaces"],
                                ["--jobs=1", "--discard_analysis_cache"])):
            with self.subTest(startup=startup):
                command = ["registry_ci.py", "run", "--module", "alpha", "--version", "1.0.0",
                           "--architecture", "amd64", "--work-dir", "/tmp/work", "--artifacts", "/tmp/artifacts",
                           *["--bazel-startup-arg=" + arg for arg in startup],
                           *["--bazel-build-arg=" + arg for arg in build]]
                with mock.patch.object(sys, "argv", command), mock.patch.object(registry_ci, "run") as execute:
                    registry_ci.main()
                execute.assert_called_once_with(registry_ci.ROOT, "alpha", "1.0.0", "amd64",
                                                Path("/tmp/work"), Path("/tmp/artifacts"), "bazel", None,
                                                startup, build, False, None)


    def test_cli_keeps_cross_compilation_and_runtime_explicit(self) -> None:
        command = ["registry_ci.py", "run", "--module", "alpha", "--version", "1.0.0",
                   "--architecture", "arm64", "--work-dir", "/tmp/work", "--artifacts", "/tmp/artifacts",
                   "--cross-compile", "--test-executor", "/opt/arm executor"]
        with mock.patch.object(sys, "argv", command), mock.patch.object(registry_ci, "run") as execute:
            registry_ci.main()
        self.assertEqual(execute.call_args.args[3], "arm64")
        self.assertEqual(execute.call_args.args[-2:], (True, Path("/opt/arm executor")))


class FetchedModuleTests(FixtureTestCase):
    def test_verified_distdir_reaches_build_test_queries_and_rust_preparation(self) -> None:
        with mock.patch.object(registry_ci, "prepare_github_sources", return_value=["--distdir=/verified/inputs"]) as prepare, \
             mock.patch.object(registry_ci, "prepare_rust", wraps=registry_ci.prepare_rust) as rust, \
             mock.patch.object(registry_ci, "run_logged", wraps=registry_ci.run_logged) as execute:
            self.run_fixture("github-inputs", build_args=["--experimental_downloader_config=/private/config"])
        self.assertEqual(prepare.call_args.args[1:4], ("alpha", "1.0.0", self.architecture))
        self.assertIn("--distdir=/verified/inputs", rust.call_args.args[-1])
        for call in execute.call_args_list:
            if call.args[0][0] == str(self.fake_bazel):
                self.assertIn("--distdir=/verified/inputs", call.args[0])
                self.assertIn("--experimental_downloader_config=/private/config", call.args[0])

    def test_github_input_failure_prevents_bazel_startup(self) -> None:
        with mock.patch.object(registry_ci, "prepare_github_sources", side_effect=registry_ci.RegistryError("unverified GitHub input")), \
             mock.patch.object(registry_ci, "run_logged") as execute:
            with self.assertRaisesRegex(registry_ci.RegistryError, "unverified GitHub input"):
                self.run_fixture("github-rejected")
        execute.assert_not_called()

    def setUp(self) -> None:
        super().setUp()
        self.registry_entry = self.entry("alpha", "1.0.0")
        self.config_path = self.registry_entry / "presubmit.json"
        self.config = json.loads(self.config_path.read_text())
        self.architecture = {"x86_64": "amd64", "aarch64": "arm64"}[registry_ci.platform.machine()]
        self.config["architectures"] = [self.architecture]
        self.config["platforms"] = {self.architecture: "@platforms//host:host"}
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
            "assert ('--test_env=HOME=' in args) == ('test' in args)\n"
            f"assert ({'--strategy=TestRunner=' + registry_ci.TEST_SANDBOX_STRATEGY!r} in args) == ('test' in args)\n"
            f"for flag in {registry_ci.HTTP_DOWNLOAD_FLAGS!r}:\n"
            "    assert (flag in args) == ('info' not in args)\n"
            f"assert {str("--experimental_downloader_config=" + str(self.root / "ci/source_mirrors.cfg"))!r} in args\n"
            "assert ('--@alpha//bazel:yang_modules=False' in args) == ('info' not in args)\n"
            "if 'info' in args:\n"
            f"    print(str(Path.cwd()) if 'execution_root' in args else {str(self.output_base)!r})\n"
            "elif 'cquery' in args:\n"
            "    print(json.dumps({'label': '@@alpha+//:library', 'trees': []}))\n"
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
        self.source_head = self.commit("Create registry validation fixture")

    def fetched_module(self, name: str) -> Path:
        return self.output_base / "external" / f"{name}+" / "MODULE.bazel"

    def run_fixture(self, suffix: str, architecture: str | None = None, image: str | None = None,
                    startup_args: list[str] | None = None, build_args: list[str] | None = None,
                    cross_compile: bool = False, test_executor: Path | None = None) -> Path:
        artifacts = self.root / f"artifacts-{suffix}"
        registry_ci.run(
            self.root, "alpha", "1.0.0", architecture or self.architecture,
            self.root / f"work-{suffix}", artifacts, str(self.fake_bazel), image, startup_args, build_args,
            cross_compile, test_executor,
        )
        return artifacts

    def test_startup_options_reach_all_bazel_commands_and_rust_preparation(self) -> None:
        commands_path = self.root / "bazel-commands.jsonl"
        self.fake_bazel.write_text(self.fake_bazel.read_text().replace(
            "args = sys.argv[1:]\n",
            "args = sys.argv[1:]\n"
            + f"with Path({str(commands_path)!r}).open('a') as log:\n"
            + "    log.write(json.dumps(args) + '\\n')\n"))
        for suffix, startup in (("default-startup", []),
                                ("custom-startup", ["--host_jvm_args=-Xmx2g",
                                                    "--host_jvm_args=-Dexample=value with spaces"])):
            with self.subTest(startup=startup):
                commands_path.write_text("")
                build = ["--jobs=1", "--discard_analysis_cache"] if startup else []
                with mock.patch.object(registry_ci, "prepare_rust", wraps=registry_ci.prepare_rust) as prepare:
                    artifacts = self.run_fixture(suffix, startup_args=startup, build_args=build)
                expected = ["--ignore_all_rc_files", f"--output_user_root={self.root / ('work-' + suffix) / 'bazel'}",
                            *startup]
                commands = [json.loads(line) for line in commands_path.read_text().splitlines()]
                self.assertEqual([command[len(expected)] for command in commands],
                                 ["build", "cquery", "info", "info", "test"])
                for command in commands:
                    self.assertEqual(command[:len(expected)], expected)
                    self.assertFalse(any(arg.startswith("--host_jvm_args=") for arg in command[len(expected):]))
                    self.assertFalse(any(arg.startswith("--action_env=CONFIG_SITE") for arg in command))
                    for flag in build:
                        self.assertEqual(flag in command, command[len(expected)] != "info")
                prepare.assert_called_once()
                self.assertEqual(prepare.call_args.args[4], [str(self.fake_bazel), *expected])
                for flag in build:
                    self.assertIn(flag, prepare.call_args.args[5])
                self.assertEqual(json.loads((artifacts / "validation.json").read_text())["bazel_startup_args"], startup)
                self.assertEqual(json.loads((artifacts / "validation.json").read_text())["bazel_build_args"], build)
                self.assertEqual(json.loads((artifacts / "validation.json").read_text())["test_sandbox_strategy"],
                                 registry_ci.TEST_SANDBOX_STRATEGY)

    def test_checkout_owned_by_another_user_retains_source_head(self) -> None:
        config = self.root / "isolated-git-config"
        config.write_text("")
        with mock.patch.dict(os.environ, {"GIT_TEST_ASSUME_DIFFERENT_OWNER": "1",
                                          "GIT_CONFIG_GLOBAL": str(config),
                                          "GIT_CONFIG_NOSYSTEM": "1"}):
            baseline = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.root,
                                      text=True, capture_output=True)
            self.assertNotEqual(baseline.returncode, 0)
            self.assertIn("dubious ownership", baseline.stderr)
            artifacts = self.run_fixture("different-owner")
        receipt = json.loads((artifacts / "source-validation.json").read_text())
        self.assertEqual(receipt["source_head"], self.source_head)
        self.assertEqual(config.read_text(), "")
        self.assertTrue(receipt["source_inputs_unchanged"])
        self.assertEqual(receipt["result"], "passed")
        self.assertEqual(receipt["native"],
                         {"system": "Linux", "machine": registry_ci.platform.machine(),
                          "userspace": self.architecture})

    def test_source_mutation_fails_and_is_recorded(self) -> None:
        source = self.registry_entry / "README.md"
        source.write_text("reviewed recipe")
        self.fake_bazel.write_text(self.fake_bazel.read_text().replace(
            "elif 'test' in args:",
            "elif 'test' in args:\n    Path(" + repr(str(source)) + ").write_text('changed')"
        ))
        with self.assertRaisesRegex(registry_ci.RegistryError, "source inputs changed"):
            self.run_fixture("changed-recipe")
        receipt = json.loads((self.root / "artifacts-changed-recipe/source-validation.json").read_text())
        self.assertFalse(receipt["source_inputs_unchanged"])
        self.assertEqual(receipt["result"], "failed: recipe inputs changed")
        self.assertEqual(receipt["source_inputs"]["README.md"],
                         hashlib.sha256(b"reviewed recipe").hexdigest())

    def declarations(self, artifacts: Path, function: str) -> list[dict]:
        # The runner generates a literal-only, Python-compatible Starlark subset.
        tree = ast.parse((artifacts / "consumer.MODULE.bazel").read_text())
        return [
            {keyword.arg: ast.literal_eval(keyword.value) for keyword in node.value.keywords}
            for node in tree.body
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Name) and node.value.func.id == function
        ]

    def test_explicit_native_host_platform_reaches_configuration_commands(self) -> None:
        self.config["architectures"] = ["amd64", "arm64"]
        self.config["platforms"] = {arch: "@alpha//:target_" + arch for arch in self.config["architectures"]}
        self.config["host_platforms"] = {arch: "@alpha//:host_" + arch for arch in self.config["architectures"]}
        write_json(self.config_path, self.config)
        script = self.fake_bazel.read_text()
        for architecture, machine in (("amd64", "x86_64"), ("arm64", "aarch64")):
            with self.subTest(architecture=architecture):
                expected = "--host_platform=" + self.config["host_platforms"][architecture]
                # Build, test and output-query commands select a configuration.
                # Read-only info path queries intentionally omit platform labels.
                self.fake_bazel.write_text(script.replace("args = sys.argv[1:]\n",
                    "args = sys.argv[1:]\n" + f"assert 'info' in args or {expected!r} in args\n"))
                # Exercise command generation, with host admission tested separately.
                native = {"system": "Linux", "machine": machine, "userspace": architecture}
                with mock.patch.object(registry_ci, "verify_native", return_value=native) as admission:
                    artifacts = self.run_fixture("host-" + architecture, architecture)
                admission.assert_called_once_with(architecture)
                validation = json.loads((artifacts / "validation.json").read_text())
                self.assertEqual(validation["host_platform"], self.config["host_platforms"][architecture])
                self.assertEqual(validation["platform"], self.config["platforms"][architecture])

    def test_kernel_runtime_download_policy_reaches_native_configuration_commands(self) -> None:
        self.config["architectures"] = ["amd64", "arm64"]
        self.config["platforms"] = {arch: "@alpha//:target_" + arch for arch in self.config["architectures"]}
        write_json(self.config_path, self.config)
        expected = "--remote_download_regex=(^|.*/)tools/build_tools/kernel_runtime_(amd64|arm64)(/.*)?$"
        script = self.fake_bazel.read_text().replace("args = sys.argv[1:]\n",
            "args = sys.argv[1:]\n"
            + f"assert ({expected!r} in args) == ('info' not in args)\n"
            + "assert '--remote_download_all' not in args\n")
        self.fake_bazel.write_text(script)
        for architecture, machine in (("amd64", "x86_64"), ("arm64", "aarch64")):
            with self.subTest(architecture=architecture):
                native = {"system": "Linux", "machine": machine, "userspace": architecture}
                with mock.patch.object(registry_ci, "verify_native", return_value=native) as admission:
                    artifacts = self.run_fixture("download-" + architecture, architecture)
                admission.assert_called_once_with(architecture)
                receipt = json.loads((artifacts / "source-validation.json").read_text())
                self.assertEqual(receipt["result"], "passed")

    def test_omitted_host_platform_preserves_bazel_default(self) -> None:
        self.fake_bazel.write_text(self.fake_bazel.read_text().replace("args = sys.argv[1:]\n",
            "args = sys.argv[1:]\nassert not any(arg.startswith('--host_platform=') for arg in args)\n"))
        artifacts = self.run_fixture("default-host")
        self.assertIsNone(json.loads((artifacts / "validation.json").read_text())["host_platform"])

    def runtime_fixture(self) -> Path:
        """A source-owned helper, executed from a separate consumer without APT."""
        helper = self.fetched.parent / "tools/runtime/prepare.py"
        helper.parent.mkdir(parents=True)
        helper.write_text(f"TEST_ARCHITECTURE = {self.architecture!r}\n" + '''import argparse, hashlib, json
from pathlib import Path
p = argparse.ArgumentParser()
p.add_argument('--lock', type=Path)
p.add_argument('--image-reference')
p.add_argument('--output', type=Path)
a = p.parse_args()
assert a.lock == Path.cwd() / 'MODULE.bazel.lock'
assert 'registry_ci_consumer' in Path('MODULE.bazel').read_text()
assert json.loads(a.lock.read_text()) == {'lockFileVersion': 13}
r = {'architecture': TEST_ARCHITECTURE, 'image_reference': a.image_reference,
     'lock_sha256': hashlib.sha256(a.lock.read_bytes()).hexdigest(),
     'runtime_libraries': {'/usr/lib/example.so': {'sha256': 'a' * 64}},
     'preserved_base_packages': {}}
r['SONIC_TEST_RUNTIME_ID'] = hashlib.sha256(json.dumps(
    {k: v for k, v in r.items() if k not in ('lock_sha256', 'preserved_base_packages')},
    sort_keys=True, separators=(',', ':')).encode()).hexdigest()
a.output.write_text(json.dumps(r))
''')
        self.config["test_runtime_preparation"] = {
            "script": "tools/runtime/prepare.py", "sha256": hashlib.sha256(helper.read_bytes()).hexdigest(),
        }
        write_json(self.config_path, self.config)
        return helper

    def test_owner_runtime_preparation_uses_consumer_lock_and_only_affects_test_flags(self) -> None:
        helper = self.runtime_fixture()
        image = "debian:trixie@sha256:" + "b" * 64
        artifacts = self.root / "artifacts-runtime"
        with mock.patch.object(registry_ci, "require_test_container") as guard, \
                mock.patch.object(registry_ci, "run_logged", wraps=registry_ci.run_logged) as execute:
            registry_ci.run(self.root, "alpha", "1.0.0", self.architecture, self.root / "work-runtime",
                            artifacts, str(self.fake_bazel), image)
        self.assertEqual(guard.call_args_list, [mock.call(image), mock.call(image)])
        commands = [call.args[0] for call in execute.call_args_list]
        self.assertIn("build", commands[0])
        self.assertIn(str(helper.resolve()), commands[1])
        self.assertIn("test", commands[2])
        receipt = json.loads((artifacts / "test-runtime.json").read_text())
        flag = "--test_env=SONIC_TEST_RUNTIME_ID=" + receipt["SONIC_TEST_RUNTIME_ID"]
        self.assertIn(flag, commands[2])
        self.assertNotIn(flag, commands[0])
        self.assertIn("--test_env=HOME=", commands[2])
        self.assertNotIn("--test_env=HOME=", commands[0])
        self.assertNotIn("--test_env=HOME=", commands[1])
        self.assertIn("--nocache_test_results", commands[2])
        self.assertTrue(set(self.config["test_targets"]).issubset(commands[2]))
        self.assertEqual((artifacts / "test-runtime-prepare.py").read_bytes(), helper.read_bytes())
        self.assertEqual((artifacts / "test-runtime.MODULE.bazel.lock").read_bytes(),
                         (artifacts / "MODULE.bazel.lock").read_bytes())
        validation = json.loads((artifacts / "validation.json").read_text())
        self.assertEqual(validation["test_runtime_flags"], [flag])
        self.assertEqual(validation["test_runtime_preparation"], self.config["test_runtime_preparation"])

    def test_runtime_setup_refuses_changed_helpers_and_fetched_module_before_execution(self) -> None:
        helper = self.runtime_fixture()
        original = helper.read_bytes()
        cases = ["checksum", "source-module", "escaped-helper"]
        for case in cases:
            with self.subTest(case=case):
                if helper.is_symlink():
                    helper.unlink()
                helper.write_bytes(original)
                self.fetched.write_bytes((self.registry_entry / "MODULE.bazel").read_bytes())
                if case == "checksum":
                    helper.write_bytes(original + b"# changed\n")
                elif case == "source-module":
                    self.fetched.write_text('module(name="alpha", version="9.0.0")\n')
                else:
                    outside = self.root / "outside.py"
                    outside.write_bytes(original)
                    helper.unlink()
                    helper.symlink_to(outside)
                with mock.patch.object(registry_ci, "require_test_container"), \
                        mock.patch.object(registry_ci, "run_logged", wraps=registry_ci.run_logged) as execute:
                    with self.assertRaises(registry_ci.RegistryError):
                        self.run_fixture(case)
                self.assertEqual(len(execute.call_args_list), 1)  # Build only, never the helper or tests.

    def test_bad_runtime_receipt_blocks_tests_and_preserves_diagnostics(self) -> None:
        self.runtime_fixture()
        real_run = registry_ci.run_logged
        other_architecture = "arm64" if self.architecture == "amd64" else "amd64"
        for field, value in (("architecture", other_architecture), ("lock_sha256", "wrong"),
                             ("image_reference", "wrong"), ("SONIC_TEST_RUNTIME_ID", "a" * 64)):
            def corrupt_receipt(command, cwd, log):
                real_run(command, cwd, log)
                if log.name == "test-runtime-preparation.log":
                    path = log.parent / "test-runtime.json"
                    receipt = json.loads(path.read_text())
                    receipt[field] = value
                    write_json(path, receipt)
            with self.subTest(field=field), mock.patch.object(registry_ci, "require_test_container"), \
                    mock.patch.object(registry_ci, "run_logged", side_effect=corrupt_receipt) as execute:
                with self.assertRaises(registry_ci.RegistryError):
                    self.run_fixture("bad-" + field, image="debian:trixie@sha256:" + "b" * 64)
                self.assertEqual(len(execute.call_args_list), 2)
                artifacts = self.root / ("artifacts-bad-" + field)
                self.assertTrue((artifacts / "test-runtime.json").is_file())
                self.assertTrue((artifacts / "test-runtime.MODULE.bazel.lock").is_file())
                self.assertFalse((artifacts / "validation.json").exists())

    def test_runtime_setup_requires_explicit_container_opt_in_before_build(self) -> None:
        self.runtime_fixture()
        with mock.patch.object(registry_ci, "run_logged") as execute:
            with self.assertRaisesRegex(registry_ci.RegistryError, "test-container-image"):
                self.run_fixture("no-container")
            execute.assert_not_called()

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
        self.assertEqual(validation["architecture"], self.architecture)
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

    def test_checked_in_integration_module_is_staged_without_mutating_reviewed_inputs(self) -> None:
        directory = self.registry_entry / "tests/integration"
        directory.mkdir(parents=True)
        (directory / "MODULE.bazel").write_text(
            'module(name = "integration_tests")\n'
            'bazel_dep(name = "alpha", version = "1.0.0")\n')
        (directory / "BUILD.bazel").write_text('# Consumer test targets\n')
        (directory / "fixture.json").write_text('reviewed fixture\n')
        before = {path.name: path.read_bytes() for path in directory.iterdir()}
        self.config.update({"integration_test_module": "tests/integration", "consumer_deps": []})
        self.config["test_targets"].append("//:archive_contract_test")
        write_json(self.config_path, self.config)
        script = self.fake_bazel.read_text()
        build, separator, test = script.partition("elif 'test' in args:")
        test = test.replace("    Path(path).write_text", (
            "    events.extend([\n"
            "        {'id': {'testResult': {'label': '@@//:archive_contract_test'}},\n"
            "         'testResult': {'status': 'PASSED', 'cachedLocally': False}},\n"
            "        {'id': {'testSummary': {'label': '@@//:archive_contract_test'}},\n"
            "         'testSummary': {'overallStatus': 'PASSED', 'totalRunCount': 1, 'totalNumCached': 0}}])\n"
            "    Path('fixture.json').write_text('private test output')\n"
            "    Path(path).write_text"))
        self.fake_bazel.write_text(build + separator + test)
        artifacts = self.run_fixture("integration")
        self.assertEqual({path.name: path.read_bytes() for path in directory.iterdir()}, before)
        staged = self.root / "work-integration/consumer"
        self.assertEqual((staged / "MODULE.bazel").read_bytes(), before["MODULE.bazel"])
        self.assertEqual((staged / "BUILD.bazel").read_bytes(), before["BUILD.bazel"])
        self.assertEqual((staged / "fixture.json").read_text(), "private test output")
        validation = json.loads((artifacts / "validation.json").read_text())
        self.assertEqual(validation["integration_test_module"], "tests/integration")
        self.assertEqual(validation["passed_tests"], self.config["test_targets"])
        self.assertTrue(validation["fetched_module_matches_registry"])
        self.assertEqual((artifacts / "consumer.MODULE.bazel").read_bytes(), before["MODULE.bazel"])
        self.fetched.write_text('module(name = "alpha", version = "2.0.0")\n')
        with self.assertRaisesRegex(registry_ci.RegistryError, "Fetched source module name/version"):
            self.run_fixture("integration-wrong-module")

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
        self.config["platforms"] = {self.architecture: "@alpha//:platform"}
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
        receipt = json.loads((artifacts / "source-validation.json").read_text())
        self.assertEqual(receipt["result"], "incomplete")
        self.assertTrue(receipt["source_inputs_unchanged"])
        self.assertEqual(receipt["source_head"], self.source_head)

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


    def test_runner_retains_bep_test_logs(self) -> None:
        self.fake_bazel.write_text(self.fake_bazel.read_text().replace(
            "elif 'test' in args:",
            "elif 'test' in args:\n"
            "    test_xml = Path.cwd().parent / 'bazel/hash/execroot/_main/bazel-out/k8-fastbuild-ST-python/testlogs/alpha/test.xml'\n"
            "    test_xml.parent.mkdir(parents=True)\n"
            "    test_xml.write_text('<testsuite/>')"
        ).replace(
            "'testResult': {'status': 'PASSED', 'cachedLocally': False}",
            "'testResult': {'status': 'PASSED', 'cachedLocally': False, "
            "'testActionOutput': [{'name': 'test.xml', 'uri': test_xml.as_uri()}]}"
        ))
        artifacts = self.run_fixture("test-logs")
        index = json.loads((artifacts / "test-results.json").read_text())
        self.assertEqual(index[0]["test"]["label"], "@@alpha+//:consumer_test")
        self.assertEqual((artifacts / index[0]["files"][0]["path"]).read_text(), '<testsuite/>')

    def test_collection_error_does_not_replace_original_test_failure(self) -> None:
        with self.fake_bazel.open("a") as script:
            script.write("\nif 'test' in args: sys.exit(42)\n")
        with mock.patch.object(registry_ci, "collect_test_logs", side_effect=registry_ci.RegistryError("Missing test log")):
            with self.assertRaisesRegex(registry_ci.RegistryError, "status 42"):
                self.run_fixture("failed-test-log")
        artifacts = self.root / "artifacts-failed-test-log"
        self.assertEqual(json.loads((artifacts / "test-results-error.json").read_text()),
                         {"error": "Missing test log"})

    def test_collection_receipt_error_does_not_replace_original_test_failure(self) -> None:
        with self.fake_bazel.open("a") as script:
            script.write("\nif 'test' in args: sys.exit(42)\n")
        original_write_text = Path.write_text

        def write_text(path: Path, *args, **kwargs):
            if path.name == "test-results-error.json":
                raise OSError("artifact filesystem full")
            return original_write_text(path, *args, **kwargs)

        with (
            mock.patch.object(registry_ci, "collect_test_logs", side_effect=OSError("copy failed")),
            mock.patch.object(Path, "write_text", autospec=True, side_effect=write_text),
        ):
            with self.assertRaisesRegex(registry_ci.RegistryError, "status 42"):
                self.run_fixture("failed-test-log-receipt")

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


    def configure_cross_fixture(self, runtime: dict | None = None) -> Path:
        self.config["architectures"] = ["amd64", "arm64"]
        self.config["platforms"] = {"amd64": "@alpha//:amd64", "arm64": "@alpha//:arm64"}
        write_json(self.config_path, self.config)
        executor = self.root / "arm executor"
        runtime = runtime or {"system": "Linux", "machine": "aarch64", "userspace": "arm64",
                              "debian_codename": "trixie"}
        executor.write_text(f"#!{sys.executable}\nimport json\nprint(json.dumps({runtime!r}))\n")
        executor.chmod(0o755)
        return executor

    def test_cross_build_keeps_host_tools_native_and_binds_external_cache_for_tests(self) -> None:
        executor = self.configure_cross_fixture()
        commands_path = self.root / "cross-bazel-commands.jsonl"
        self.fake_bazel.write_text(self.fake_bazel.read_text().replace(
            "args = sys.argv[1:]\n", "args = sys.argv[1:]\n"
            + f"with Path({str(commands_path)!r}).open('a') as log:\n"
            + "    log.write(json.dumps(args) + '\\n')\n"))
        image = "runner@sha256:" + "a" * 64
        native = {"system": "Linux", "machine": "x86_64", "userspace": "amd64"}
        for suffix, host_platform in (("default-cross", "@alpha//:amd64"),
                                      ("explicit-cross", "@alpha//:exec_amd64")):
            with self.subTest(host_platform=host_platform):
                if suffix == "explicit-cross":
                    self.config["host_platforms"] = {"amd64": host_platform, "arm64": "@alpha//:exec_arm64"}
                    write_json(self.config_path, self.config)
                commands_path.write_text("")
                adapted = {"target_platform": "//_registry_ci_cross:arm64",
                           "execution_platform": "//_registry_ci_cross:amd64",
                           "declared_execution_platform": host_platform,
                           "selected_module_versions": {},
                           "module_versions_unchanged": True}
                with mock.patch.object(registry_ci, "verify_native", return_value=native) as admission, \
                        mock.patch.object(registry_ci, "require_test_container") as container, \
                        mock.patch.object(registry_ci.cross_toolchain, "prepare", return_value=adapted) as adapter:
                    artifacts = self.run_fixture(suffix, architecture="arm64", image=image,
                                                 cross_compile=True, test_executor=executor)
                self.assertEqual(adapter.call_args.args[-3:-1], ("@alpha//:arm64", host_platform))
                admission.assert_called_once_with("amd64")
                container.assert_called_once_with(image)
                commands = [json.loads(line) for line in commands_path.read_text().splitlines()]
                for command in commands:
                    if "info" not in command:
                        self.assertIn("--host_platform=//_registry_ci_cross:amd64", command)
                        self.assertIn("--platforms=//_registry_ci_cross:arm64", command)
                    wrappers = [arg for arg in command if arg.startswith("--run_under=")]
                    self.assertEqual(bool(wrappers), "test" in command)
                    if wrappers:
                        self.assertEqual(registry_ci.shlex.split(wrappers[0].split("=", 1)[1]),
                                         [str(executor), "--bind", "/tmp", "--bind", str(self.root / ("work-" + suffix)),
                                          "--bind", str(artifacts), "--bind", str(self.output_base), "--"])
                evidence = json.loads((artifacts / "validation.json").read_text())
                self.assertEqual(evidence["execution_architecture"], "amd64")
                self.assertEqual(evidence["architecture"], "arm64")
                self.assertTrue(evidence["cross_compile"])
                self.assertEqual(evidence["test_execution"], "qemu-aarch64")
                self.assertEqual(evidence["test_container_image"], image)
                self.assertEqual(evidence["host_platform"], "//_registry_ci_cross:amd64")
                self.assertEqual(evidence["cross_platforms"], adapted)
                autoconf = evidence["cross_runtime"]["autoconf"]
                self.assertTrue(autoconf["enabled"])
                for command in commands:
                    if "build" in command or "test" in command:
                        self.assertTrue(set(autoconf["flags"]).issubset(command))
                self.assertEqual(evidence["cross_runtime"]["executor_sha256"],
                                 hashlib.sha256(executor.read_bytes()).hexdigest())
                self.assertEqual(json.loads((artifacts / "source-validation.json").read_text())["native"], native)

    def test_emulated_timeout_defaults_are_test_only_and_preserve_explicit_limits(self) -> None:
        executor = self.configure_cross_fixture()
        commands_path = self.root / "timeout-bazel-commands.jsonl"
        self.fake_bazel.write_text(self.fake_bazel.read_text().replace(
            "args = sys.argv[1:]\n", "args = sys.argv[1:]\n"
            + f"with Path({str(commands_path)!r}).open('a') as log:\n"
            + "    log.write(json.dumps(args) + '\\n')\n"))
        default = "--test_timeout=180,900,2700,7200"
        adapted = {"target_platform": "//_registry_ci_cross:arm64",
                   "execution_platform": "//_registry_ci_cross:amd64",
                   "selected_module_versions": {}}
        for suffix, cross, caller in (
                ("native", False, []),
                ("native-explicit", False, ["--test_timeout=42"]),
                ("emulated", True, []),
                ("caller-scalar", True, ["--test_timeout=42"]),
                ("caller-tiers", True, ["--test_timeout=10,20,30,40"]),
                ("caller-separate", True, ["--test_timeout", "47"])):
            with self.subTest(case=suffix):
                commands_path.write_text("")
                with mock.patch.object(registry_ci, "verify_native", return_value={"userspace": "amd64"}), \
                        mock.patch.object(registry_ci, "require_test_container"), \
                        mock.patch.object(registry_ci.cross_toolchain, "prepare", return_value=adapted):
                    artifacts = self.run_fixture(suffix, architecture="arm64" if cross else "amd64",
                                                 build_args=caller, cross_compile=cross,
                                                 test_executor=executor if cross else None)
                commands = [json.loads(line) for line in commands_path.read_text().splitlines()]
                test_command, = [command for command in commands if "test" in command]
                timeouts = [arg for arg in test_command
                            if arg == "--test_timeout" or arg.startswith("--test_timeout=")]
                expected = [caller[0]] if caller else ([default] if cross else [])
                self.assertEqual(timeouts, expected)
                if caller == ["--test_timeout", "47"]:
                    self.assertEqual(test_command[test_command.index("--test_timeout") + 1], "47")
                for command in commands:
                    if "test" not in command:
                        self.assertNotIn(default, command)
                evidence = json.loads((artifacts / "validation.json").read_text())
                self.assertEqual(default in evidence["test_runtime_flags"], cross and not caller)

    def test_cross_runtime_must_match_target_architecture_and_distribution(self) -> None:
        expected = {"system": "Linux", "machine": "aarch64", "userspace": "arm64", "debian_codename": "trixie"}
        for field, value in (("system", "Darwin"), ("machine", "x86_64"),
                             ("userspace", "amd64"), ("debian_codename", "bookworm")):
            with self.subTest(field=field):
                executor = self.configure_cross_fixture({**expected, field: value})
                with mock.patch.object(registry_ci, "verify_native", return_value={"userspace": "amd64"}), \
                        mock.patch.object(registry_ci, "require_test_container"), \
                        mock.patch.object(registry_ci, "prepare_rust") as prepare:
                    with self.assertRaisesRegex(registry_ci.RegistryError, "ARM64 Debian Trixie runtime"):
                        self.run_fixture("wrong-runtime-" + field, architecture="arm64",
                                         cross_compile=True, test_executor=executor)
                prepare.assert_not_called()

    def test_cross_compilation_rejects_other_directions_or_missing_executor(self) -> None:
        executor = self.configure_cross_fixture()
        for target, cross, selected, error in (
                ("amd64", True, executor, "ARM64 targets on AMD64"),
                ("amd64", False, executor, "requires explicit cross compilation"),
                ("arm64", True, None, "absolute --test-executor"),
                ("arm64", True, Path("relative-executor"), "absolute --test-executor")):
            with self.subTest(target=target, cross=cross, executor=selected), \
                    mock.patch.object(registry_ci, "verify_native", return_value={"userspace": "amd64"}), \
                    mock.patch.object(registry_ci, "require_test_container"):
                with self.assertRaisesRegex(registry_ci.RegistryError, error):
                    self.run_fixture("invalid-cross", architecture=target, cross_compile=cross,
                                     test_executor=selected)

    def test_cross_runtime_preparation_executes_owner_helper_through_guest(self) -> None:
        self.architecture = "arm64"
        helper = self.runtime_fixture()
        consumer = self.root / "cross runtime consumer"
        consumer.mkdir()
        (consumer / "MODULE.bazel").write_text('module(name = "registry_ci_consumer")\n')
        write_json(consumer / "MODULE.bazel.lock", {"lockFileVersion": 13})
        artifacts = self.root / "cross runtime artifacts"
        artifacts.mkdir()
        captured = artifacts / "guest-command.json"
        executor = self.root / "guest executor"
        executor.write_text(
            "#!/usr/bin/python3 -IS\n"
            "import json, os, sys\nfrom pathlib import Path\n"
            "command = sys.argv[sys.argv.index('--') + 1:]\n"
            "assert command[0] == '/usr/bin/python3'\n"
            f"Path({str(captured)!r}).write_text(json.dumps(sys.argv[1:]))\n"
            "os.execv(sys.executable, [sys.executable, '-I', '-S', *command[1:]])\n"
        )
        executor.chmod(0o755)
        prefix = [str(executor), "--bind", str(self.output_base),
                  "--bind", str(consumer), "--bind", str(artifacts), "--"]
        image = "debian:trixie@sha256:" + "b" * 64
        with mock.patch.object(registry_ci, "require_test_container") as guard:
            flags = registry_ci.prepare_test_runtime(
                self.config, self.fetched.parent, consumer, artifacts, "arm64", image, prefix)
        guard.assert_called_once_with(image)
        command = json.loads(captured.read_text())
        self.assertEqual(command[:len(prefix) - 1], prefix[1:])
        self.assertEqual(command[len(prefix) - 1:len(prefix) + 2],
                         ["/usr/bin/python3", "-B", str(helper.resolve())])
        receipt = json.loads((artifacts / "test-runtime.json").read_text())
        self.assertEqual(receipt["architecture"], "arm64")
        self.assertEqual(flags, ["--test_env=SONIC_TEST_RUNTIME_ID=" + receipt["SONIC_TEST_RUNTIME_ID"]])
        self.assertEqual((artifacts / "test-runtime-prepare.py").read_bytes(), helper.read_bytes())
        self.assertEqual((artifacts / "test-runtime.MODULE.bazel.lock").read_bytes(),
                         (consumer / "MODULE.bazel.lock").read_bytes())


if __name__ == "__main__":
    unittest.main()
