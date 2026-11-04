"""Regression coverage for CI platform adaptation and provider isolation."""

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock


SPEC = importlib.util.spec_from_file_location("cross_toolchain_tested", Path(__file__).resolve().parents[1] / "cross_toolchain.py")
cross = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cross)


class CrossToolchainTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.consumer, self.artifacts = self.root / "consumer", self.root / "artifacts"
        self.consumer.mkdir()
        self.artifacts.mkdir()
        self.original = 'module(name="existing_integration")\nbazel_dep(name="alpha", version="1.2")\n'
        (self.consumer / "MODULE.bazel").write_text(self.original)
        (self.consumer / "BUILD.bazel").write_text('exports_files(["existing.data"])\n')
        (self.consumer / "existing.data").write_text("preserve copied integration inputs")
        self.versions = {"alpha": "1.2", "platforms": "1.0.0", "rules_cc": "0.2.4"}

    def test_host_parent_gets_explicit_target_cpu_without_replacing_integration_files(self):
        original_build = (self.consumer / "BUILD.bazel").read_bytes()
        result = cross.write_platforms(self.consumer, "@platforms//host:host", "@local_config_platform//:host",
                                       "platforms", "@registry_ci_cross_cc//:trixie")
        generated = (self.consumer / cross.PACKAGE / "BUILD.bazel").read_text()
        self.assertIn('parents=["@platforms//host:host"]', generated)
        self.assertIn('parents=["@local_config_platform//:host"]', generated)
        self.assertIn('"@platforms//cpu:aarch64"', generated)
        self.assertIn('"@platforms//cpu:x86_64"', generated)
        self.assertEqual(result["target_platform"], "//_registry_ci_cross:arm64")
        self.assertEqual((self.consumer / "MODULE.bazel").read_text(), self.original)
        self.assertEqual((self.consumer / "BUILD.bazel").read_bytes(), original_build)
        self.assertEqual((self.consumer / "existing.data").read_text(), "preserve copied integration inputs")
        with self.assertRaisesRegex(ValueError, "already exists"):
            cross.write_platforms(self.consumer, "@platforms//host:host", "@platforms//host:host", "platforms", ":trixie")

    def test_alias_uses_existing_selected_version_and_preserves_custom_repository_name(self):
        self.assertEqual(cross.expose_dependency(self.consumer, "rules_cc", self.versions), "rules_cc")
        self.assertIn('bazel_dep(name="rules_cc", version="0.2.4")', (self.consumer / "MODULE.bazel").read_text())
        path = self.consumer / "MODULE.bazel"
        path.write_text(self.original + 'bazel_dep(name="rules_cc", version="0.1.0", repo_name="existing_cc")\n')
        before = path.read_bytes()
        self.assertEqual(cross.expose_dependency(self.consumer, "rules_cc", self.versions), "existing_cc")
        self.assertEqual(path.read_bytes(), before)
        with self.assertRaisesRegex(ValueError, "original module graph"):
            cross.expose_dependency(self.consumer, "missing", self.versions)

    def test_rich_platform_keeps_published_compiler_and_inherited_constraints(self):
        with mock.patch.object(cross, "module_graph", return_value=self.versions), \
                mock.patch.object(cross, "prepare_provider") as provider:
            result = cross.prepare(self.root, self.consumer, self.root, self.artifacts, ["bazel"], [],
                                   "@sonic_build_infra//platforms:aarch64_trixie",
                                   "@sonic_build_infra//platforms:x86_64_trixie", mock.Mock())
        provider.assert_not_called()
        self.assertIsNone(result["provider"])
        self.assertEqual(result["distribution_constraint"], "@sonic_build_infra//platforms:trixie")
        self.assertTrue(result["module_versions_unchanged"])
        self.assertNotIn('register_toolchains', (self.consumer / "MODULE.bazel").read_text())

    def test_dependency_graph_changes_fail_instead_of_silently_upgrading(self):
        with mock.patch.object(cross, "module_graph", side_effect=[self.versions, {**self.versions, "rules_cc": "0.2.22"}]):
            with self.assertRaisesRegex(ValueError, "changed the consumer"):
                cross.prepare(self.root, self.consumer, self.root, self.artifacts, ["bazel"], [],
                              "@sonic_build_infra//platforms:aarch64_trixie",
                              "@sonic_build_infra//platforms:x86_64_trixie", mock.Mock())

    def test_provider_is_separately_pinned_retains_manifests_and_shuts_down(self):
        entry = self.root / "modules/sonic-build-infra" / cross.PROVIDER_VERSION
        entry.mkdir(parents=True)
        (entry / "MODULE.bazel").write_text('module(name="sonic-build-infra")\n')
        (entry / "source.json").write_text('{"integrity":"original-provider-integrity"}\n')
        commands = []

        def run(command, cwd, log):
            commands.append(command)
            if "fetch" not in command:
                return
            external = cwd / "bazel-output/external"
            compiler = external / cross.COMPILER_REPOSITORY
            sysroot = external / cross.SYSROOT_REPOSITORY
            (compiler / "usr/bin").mkdir(parents=True)
            (sysroot / "root").mkdir(parents=True)
            (external / "sonic-build-infra+").mkdir()
            (external / "sonic-build-infra+/MODULE.bazel").write_bytes((entry / "MODULE.bazel").read_bytes())
            (compiler / "usr/bin/aarch64-linux-gnu-gcc-14").write_bytes(b"\x7fELF" + b"\0" * 14 + b"\x3e\0")
            (compiler / "inputs.json").write_text('{"compiler":"locked packages"}\n')
            (sysroot / "inputs.json").write_text('{"sysroot":"locked packages"}\n')
            (cwd / "MODULE.bazel.lock").write_text('{"original":"provider resolution"}\n')

        provider = cross.prepare_provider(self.root, self.root, self.artifacts,
                                          ["bazel", "--output_base=/consumer-cache"],
                                          ["--registry=file:///registry", "--platforms=@old//:arm64",
                                           "--override_module=sonic-build-infra=/unrelated", "--http_connector_attempts=12"], run)
        self.assertEqual(provider["version"], cross.PROVIDER_VERSION)
        self.assertEqual(provider["compiler_elf_machine"], 62)
        self.assertIn("--repo=@registry_ci_gcc", commands[0])
        self.assertIn("--repo=@registry_ci_sysroot", commands[0])
        self.assertIn("--output_base=" + str(self.root / "cross-provider/bazel-output"), commands[0])
        self.assertFalse(any(x.startswith(("--platforms=", "--override_module=")) for x in commands[0]))
        self.assertEqual(commands[-1][-1], "shutdown")
        self.assertEqual((self.consumer / "MODULE.bazel").read_text(), self.original)
        for name in ("cross-compiler-inputs.json", "cross-sysroot-inputs.json", "cross-provider.MODULE.bazel.lock"):
            self.assertTrue((self.artifacts / name).is_file(), name)

    def test_multiple_selected_versions_are_not_aliased_ambiguously(self):
        graph = {"key": "<root>", "dependencies": [{"key": "cc@1", "name": "cc", "version": "1"},
                                                  {"key": "cc@2", "name": "cc", "version": "2"}]}
        with self.assertRaisesRegex(ValueError, "multiple selected versions"):
            cross.selected_versions(graph)


if __name__ == "__main__":
    unittest.main()
