"""Regression coverage for CI platform adaptation and provider isolation."""

import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
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
        self.case_count = 0

    def prepare_case(self, versions, target_parent="@sonic_build_infra//platforms:aarch64_trixie",
                     execution_parent="@sonic_build_infra//platforms:x86_64_trixie", after=None):
        case = self.root / f"case-{self.case_count}"
        self.case_count += 1
        consumer, artifacts = case / "consumer", case / "artifacts"
        shutil.copytree(self.consumer, consumer)
        artifacts.mkdir()
        if "sonic-build-infra" in versions:
            # The selected version can differ from the consumer's minimum.
            module = consumer / "MODULE.bazel"
            module.write_text(module.read_text() + 'bazel_dep(name="sonic-build-infra", '
                              'version="0.0.13-ff408bafc35ce0e3d7a0bd27803debdc2a921de6")\n')
        compiler, sysroot = case / "compiler", case / "sysroot"
        for name in ("bin", "usr", "aarch64-linux-gnu"):
            (compiler / name).mkdir(parents=True)
        (compiler / "inputs.json").write_text('{"compiler":"locked packages"}\n')
        (sysroot / "usr/include").mkdir(parents=True)
        (sysroot / "usr/include/features.h").write_text("/* locked sysroot header */\n")
        provider_value = {"module": "sonic-build-infra", "version": cross.PROVIDER_VERSION,
                          "compiler": str(compiler), "sysroot": str(sysroot)}
        with mock.patch.object(cross, "module_graph", side_effect=[versions, versions if after is None else after]), \
                mock.patch.object(cross, "prepare_provider", return_value=provider_value) as provider:
            result = cross.prepare(self.root, consumer, case, artifacts, ["bazel"], [],
                                   target_parent, execution_parent, mock.Mock())
        return result, consumer, artifacts, provider

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

    def test_proven_selected_versions_keep_published_compiler_and_inherited_constraints(self):
        self.assertIn(cross.PROVIDER_VERSION, cross.VERIFIED_SONIC_CROSS_VERSIONS)
        for version in sorted(cross.VERIFIED_SONIC_CROSS_VERSIONS):
            for target in sorted(cross.SONIC_PLATFORMS):
                with self.subTest(version=version, target=target):
                    execution = target.replace(":aarch64_trixie", ":x86_64_trixie")
                    versions = {**self.versions, "sonic-build-infra": version}
                    result, consumer, artifacts, provider = self.prepare_case(versions, target, execution)
                    provider.assert_not_called()
                    self.assertIsNone(result["provider"])
                    self.assertTrue(result["use_published_cross_toolchain"])
                    self.assertEqual(result["selected_sonic_build_infra_version"], version)
                    self.assertEqual(result["selected_module_versions"], versions)
                    self.assertEqual(result["distribution_constraint"], target.rsplit(":", 1)[0] + ":trixie")
                    self.assertTrue(result["module_versions_unchanged"])
                    generated = (consumer / cross.PACKAGE / "BUILD.bazel").read_text()
                    self.assertIn(f'parents=["{target}"]', generated)
                    self.assertIn(f'parents=["{execution}"]', generated)
                    self.assertNotIn("register_toolchains", (consumer / "MODULE.bazel").read_text())
                    self.assertFalse((artifacts / "cross-adapter.BUILD.bazel").exists())

    def test_native_only_and_unknown_selected_versions_use_provider_with_original_parents(self):
        for version in ("0.0.6-553b2f70f9ba77b74befdf77674894166139ddcc",
                        "0.0.13-ff408bafc35ce0e3d7a0bd27803debdc2a921de6",
                        "0.0.25", "0.0.99-unverified", None):
            with self.subTest(version=version):
                versions = dict(self.versions)
                if version is not None:
                    versions["sonic-build-infra"] = version
                result, consumer, artifacts, provider = self.prepare_case(versions)
                provider.assert_called_once()
                self.assertEqual(result["provider"]["version"], cross.PROVIDER_VERSION)
                self.assertFalse(result["use_published_cross_toolchain"])
                self.assertEqual(result["selected_sonic_build_infra_version"], version)
                self.assertEqual(result["selected_module_versions"], versions)
                self.assertTrue(result["module_versions_unchanged"])
                generated = (consumer / cross.PACKAGE / "BUILD.bazel").read_text()
                self.assertIn('parents=["@sonic_build_infra//platforms:aarch64_trixie"]', generated)
                self.assertIn('parents=["@sonic_build_infra//platforms:x86_64_trixie"]', generated)
                self.assertIn('"@platforms//cpu:aarch64"', generated)
                self.assertIn('"@platforms//cpu:x86_64"', generated)
                self.assertIn('"@registry_ci_cross_cc//:trixie"', generated)
                adapter = (artifacts / "cross-adapter.BUILD.bazel").read_text()
                self.assertIn('constraint_setting(name="distribution")', adapter)
                self.assertIn('constraint_value(name="trixie", constraint_setting=":distribution")', adapter)
                self.assertIn('register_toolchains("@registry_ci_cross_cc//:toolchain")',
                              (consumer / "MODULE.bazel").read_text())
                self.assertEqual((consumer / "BUILD.bazel").read_bytes(),
                                 (self.consumer / "BUILD.bazel").read_bytes())
                self.assertEqual((consumer / "existing.data").read_text(), "preserve copied integration inputs")
                self.assertEqual(json.loads((artifacts / "cross-platforms.json").read_text()), result)

    def test_proven_version_requires_recognized_parent_to_reuse_published_compiler(self):
        versions = {**self.versions, "sonic-build-infra": cross.PROVIDER_VERSION}
        target, execution = "//custom:arm_with_extra_constraints", "@platforms//host:host"
        result, consumer, artifacts, provider = self.prepare_case(versions, target, execution)
        provider.assert_called_once()
        self.assertFalse(result["use_published_cross_toolchain"])
        generated = (consumer / cross.PACKAGE / "BUILD.bazel").read_text()
        self.assertIn(f'parents=["{target}"]', generated)
        self.assertIn(f'parents=["{execution}"]', generated)
        self.assertEqual(result["selected_module_versions"], versions)

    def test_dependency_graph_changes_fail_instead_of_silently_upgrading(self):
        for version in (cross.PROVIDER_VERSION, "0.0.13-ff408bafc35ce0e3d7a0bd27803debdc2a921de6"):
            with self.subTest(version=version):
                versions = {**self.versions, "sonic-build-infra": version}
                with self.assertRaisesRegex(ValueError, "changed the consumer"):
                    self.prepare_case(versions, after={**versions, "rules_cc": "0.2.22"})

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


class ModuleGraphStatusTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.graph = {"key": "<root>", "name": "consumer", "version": "", "root": True,
                      "dependencies": [{"key": "alpha@2", "name": "alpha", "version": "2",
                                        "dependencies": [], "indirectDependencies": [], "cycles": []}],
                      "indirectDependencies": [], "cycles": []}

    def resolve(self, code=0, errors="", graph=None):
        def run(command, **kwargs):
            self.assertIn("--from=<root>", command)
            self.assertIn("--depth=-1", command)
            self.assertIn("--noinclude_unused", command)
            self.assertIn("--extension_info=hidden", command)
            kwargs["stdout"].write(json.dumps(self.graph if graph is None else graph))
            kwargs["stderr"].write(errors)
            return subprocess.CompletedProcess(command, code)
        with mock.patch.object(cross.subprocess, "run", side_effect=run):
            return cross.module_graph(["bazel"], [], self.root, self.root, "graph")

    def test_complete_versions_survive_only_extension_inspection_failure(self):
        for code, errors in ((0, ""), (2, "ERROR: unused extension failed\n"
                                     "ERROR: Results may be incomplete as 1 extension failed.\n")):
            self.assertEqual(self.resolve(code, errors), {"alpha": "2"})
            receipt = json.loads((self.root / "graph-status.json").read_text())
            self.assertEqual(receipt["returncode"], code)
            self.assertTrue(receipt["module_resolution_complete"])
            self.assertEqual(receipt["extension_inspection_complete"], code == 0)
            self.assertEqual((self.root / "graph.stderr").read_text(), errors)

    def test_resolution_and_other_command_failures_remain_fatal(self):
        marker = "ERROR: Results may be incomplete as 1 extension failed.\n"
        for code, errors in ((37, "resolution failed"), (1, marker), (2, "bad option"),
                             (2, marker + "ERROR: another failure\n"), (2, "")):
            with self.subTest(code=code, errors=errors), self.assertRaises(subprocess.CalledProcessError):
                self.resolve(code, errors)
            receipt = json.loads((self.root / "graph-status.json").read_text())
            self.assertFalse(receipt["module_resolution_complete"])

    def test_partial_or_inconsistent_graphs_are_never_accepted(self):
        for graph in ({}, {**self.graph, "root": False},
                      {**self.graph, "dependencies": [{"key": "alpha@2", "name": "alpha",
                                                       "version": "2", "unexpanded": True}]},
                      {**self.graph, "dependencies": [{"key": "alpha@1", "name": "alpha",
                                                       "version": "2"}]}):
            for code in (0, 2):
                with self.subTest(graph=graph, code=code), self.assertRaises(ValueError):
                    self.resolve(code, "ERROR: Results may be incomplete as 2 extensions failed.\n", graph)
                self.assertFalse(json.loads((self.root / "graph-status.json").read_text())[
                    "module_resolution_complete"])


if __name__ == "__main__":
    unittest.main()
