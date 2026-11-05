"""Analyze link features without executing a compiler or fetching an ARM SDK."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ADAPTER = Path(__file__).resolve().parents[1] / "cross_cc_toolchain.bzl"
LINK_ACTIONS = [
    "c++-link-executable", "c++-link-dynamic-library", "c++-link-nodeps-dynamic-library",
    "lto-index-for-executable", "lto-index-for-dynamic-library",
    "lto-index-for-nodeps-dynamic-library",
]

FIXTURE = '''
load("@bazel_tools//tools/cpp:cc_toolchain_config_lib.bzl", "tool_path")

def _legacy(ctx):
    # Control: Bazel's generated legacy action configurations force stripping
    # even when a caller lists that feature as unsupported.
    return cc_common.create_cc_toolchain_config_info(
        ctx = ctx, toolchain_identifier = "legacy-control",
        host_system_name = "x86_64-linux-gnu", target_system_name = "aarch64-linux-gnu",
        target_cpu = "aarch64", target_libc = "glibc", compiler = "gcc",
        abi_version = "aarch64", abi_libc_version = "glibc",
        tool_paths = [tool_path(name = name, path = "compiler/bin/aarch64-linux-gnu-gcc")
                      for name in ["gcc", "ld", "ar", "cpp", "gcov", "nm", "objdump", "strip"]],
    )

legacy_config = rule(implementation = _legacy, provides = [CcToolchainConfigInfo])

def _probe(ctx):
    cc = ctx.attr.cc[cc_common.CcToolchainInfo]
    features = cc_common.configure_features(
        ctx = ctx, cc_toolchain = cc, unsupported_features = ctx.attr.unsupported,
    )
    reports = []
    outputs = []
    for action in ACTIONS:
        variables = cc_common.create_link_variables(
            cc_toolchain = cc, feature_configuration = features,
            output_file = "sentinel-output", user_link_flags = ["-Wl,--as-needed"],
            library_search_directories = depset(["/sentinel/lib"]),
            runtime_library_search_directories = depset(["/sentinel/rpath"]),
            is_linking_dynamic_library = "dynamic-library" in action,
            must_keep_debug = ctx.attr.keep_debug,
        )
        flags = cc_common.get_memory_inefficient_command_line(
            feature_configuration = features, action_name = action, variables = variables,
        )
        tool = cc_common.get_tool_for_action(feature_configuration = features, action_name = action)
        reports.append({
            "action": action, "tool": tool, "flags": flags,
            "enabled": cc_common.action_is_enabled(feature_configuration = features, action_name = action),
            "strip": cc_common.is_enabled(feature_configuration = features, feature_name = "strip_debug_symbols"),
        })
        output = ctx.actions.declare_file(ctx.label.name + "/" + action)
        outputs.append(output)
        # aquery inspects these actions; none may execute. No compiler exists.
        ctx.actions.run(executable = tool, arguments = flags,
                        outputs = [output], mnemonic = "FeatureLinkProbe")
    print("CROSS_FEATURE_REPORT=" + json.encode({"case": ctx.label.name, "links": reports}))
    return [DefaultInfo(files = depset(outputs))]

feature_probe = rule(implementation = _probe, fragments = ["cpp"], attrs = {
    "cc": attr.label(default = Label("//:cc")),
    "unsupported": attr.string_list(), "keep_debug": attr.bool(),
})
'''

BUILD = '''
load(":adapter.bzl", "linux_aarch64_gcc")
load(":fixture.bzl", "legacy_config", "feature_probe")
platform(name = "fixture_platform")
filegroup(name = "empty")
linux_aarch64_gcc(name = "config", compiler_anchor = "compiler/inputs.json",
                  sysroot_anchor = "sysroot/usr/include/features.h")
legacy_config(name = "legacy_config")
[
    cc_toolchain(name = name, toolchain_config = config,
                 all_files = ":empty", compiler_files = ":empty", linker_files = ":empty",
                 strip_files = ":empty", dwp_files = ":empty", objcopy_files = ":empty",
                 ar_files = ":empty", supports_param_files = 1)
    for name, config in [("cc", ":config"), ("legacy_cc", ":legacy_config")]
]
feature_probe(name = "legacy_disabled", cc = ":legacy_cc", unsupported = ["strip_debug_symbols"])
feature_probe(name = "default")
feature_probe(name = "disabled", unsupported = ["strip_debug_symbols"])
feature_probe(name = "keep_debug", keep_debug = True)
'''


@unittest.skipUnless(os.environ.get("REGISTRY_CI_TEST_BAZEL"),
                     "set REGISTRY_CI_TEST_BAZEL for the real Bazel feature analysis")
class CrossToolchainFeatureIntegrationTest(unittest.TestCase):
    def test_disabled_stripping_preserves_all_link_actions_and_default_flags(self):
        with tempfile.TemporaryDirectory(prefix="registry-cross-features-") as temporary:
            work = Path(temporary)
            consumer, artifacts = work / "consumer", work / "artifacts"
            consumer.mkdir()
            artifacts.mkdir()
            (consumer / "MODULE.bazel").write_text(
                'module(name = "cross_feature_fixture")\n'
                'bazel_dep(name = "rules_cc", version = "0.1.1")\n')
            (consumer / "BUILD.bazel").write_text(BUILD)
            (consumer / "fixture.bzl").write_text(FIXTURE.replace(
                "\ndef _legacy", "\nACTIONS = " + repr(LINK_ACTIONS) + "\n\ndef _legacy"))
            shutil.copyfile(ADAPTER, consumer / "adapter.bzl")
            for name in ("compiler/inputs.json", "sysroot/usr/include/features.h"):
                path = consumer / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("analysis-only anchor\n")
            prefix = [os.environ["REGISTRY_CI_TEST_BAZEL"], "--batch", "--ignore_all_rc_files",
                      "--host_jvm_args=-Xmx512m", "--output_user_root=" + str(work / "bazel"),
                      "aquery", "--incompatible_autoload_externally=", "--lockfile_mode=off",
                      "--host_platform=//:fixture_platform", "--platforms=//:fixture_platform",
                      "--jobs=1", "--loading_phase_threads=1", "--remote_cache=", "--disk_cache=",
                      "--output=jsonproto"]

            def analyze(case: str, expression: str):
                command = [*prefix, expression]
                (artifacts / (case + "-command.json")).write_text(json.dumps(command, indent=2) + "\n")
                output_path, log_path = artifacts / (case + "-aquery.json"), artifacts / (case + ".log")
                with output_path.open("w") as output, log_path.open("w") as log:
                    result = subprocess.run(command, cwd=consumer, stdout=output,
                                            stderr=log, timeout=180)
                return result.returncode, log_path.read_text(), output_path

            try:
                code, transcript, _ = analyze("legacy", "//:legacy_disabled")
                self.assertNotEqual(code, 0, transcript)
                self.assertIn("unconditionally implies feature 'strip_debug_symbols'", transcript)
                self.assertIn("unsupported by this rule", transcript)
                code, transcript, output = analyze("production", "set(//:default //:disabled //:keep_debug)")
                self.assertEqual(code, 0, transcript)
                reports = {}
                marker = "CROSS_FEATURE_REPORT="
                for line in transcript.splitlines():
                    if marker in line:
                        value = json.loads(line.split(marker, 1)[1])
                        self.assertNotIn(value["case"], reports)
                        reports[value["case"]] = value["links"]
                self.assertEqual(set(reports), {"default", "disabled", "keep_debug"})
                for case, links in reports.items():
                    self.assertEqual([link["action"] for link in links], LINK_ACTIONS)
                    for link in links:
                        with self.subTest(case=case, action=link["action"]):
                            self.assertTrue(link["enabled"])
                            self.assertEqual(link["strip"], case != "disabled")
                            self.assertTrue(link["tool"].endswith("compiler/bin/aarch64-linux-gnu-gcc"))
                            self.assertEqual("-Wl,-S" in link["flags"], case == "default")
                            for flag in ("-o", "sentinel-output", "-L/sentinel/lib", "-Wl,--as-needed", "--sysroot=sysroot"):
                                self.assertIn(flag, link["flags"])
                            self.assertTrue(any("/sentinel/rpath" in flag for flag in link["flags"]))
                            self.assertEqual("-shared" in link["flags"], "dynamic-library" in link["action"])
                for default, disabled, keep_debug in zip(reports["default"], reports["disabled"], reports["keep_debug"]):
                    self.assertEqual([flag for flag in default["flags"] if flag != "-Wl,-S"], disabled["flags"])
                    self.assertEqual(disabled["flags"], keep_debug["flags"])
                actions = [action for action in json.loads(output.read_text())["actions"]
                           if action.get("mnemonic") == "FeatureLinkProbe"]
                self.assertEqual(len(actions), 3 * len(LINK_ACTIONS))
                self.assertTrue(all(action["arguments"][0].endswith("compiler/bin/aarch64-linux-gnu-gcc")
                                    for action in actions))
                self.assertFalse((consumer / "compiler/bin").exists())
                (artifacts / "result.json").write_text(json.dumps({
                    "legacy_rejection_reproduced": True, "analysis_only": True,
                    "analyzed_link_actions": len(actions), "reports": reports,
                    "adapter_sha256": hashlib.sha256((consumer / "adapter.bzl").read_bytes()).hexdigest(),
                }, indent=2) + "\n")
            finally:
                shutil.copytree(consumer, artifacts / "inputs", ignore=shutil.ignore_patterns("bazel-*"))
                destination = os.environ.get("REGISTRY_CI_TEST_ARTIFACTS")
                if destination:
                    shutil.copytree(artifacts, Path(destination) / work.name)


if __name__ == "__main__":
    unittest.main()
