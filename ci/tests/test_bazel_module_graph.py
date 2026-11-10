"""Real module resolution without compiler, SDK, or network dependencies."""

import base64
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import unittest


SPEC = importlib.util.spec_from_file_location("graph_cross", Path(__file__).resolve().parents[1] / "cross_toolchain.py")
cross = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cross)

# Local stand-ins for Bazel 8.5.1's embedded MODULE.bazel dependencies. They
# exercise its real resolver/inspector, without fetching SDKs or public modules.
BUILTINS = {
    "rules_license": "1.0.0", "buildozer": "7.1.2", "platforms": "0.0.11",
    "zlib": "1.3.1.bcr.5", "rules_proto": "7.0.2", "bazel_features": "1.30.0",
    "protobuf": "29.0", "rules_java": "8.14.0", "rules_cc": "0.1.1",
    "rules_python": "0.40.0", "rules_shell": "0.2.0", "apple_support": "1.23.1",
}


def write_fixture(root):
    registry = root / "registry"
    registry.mkdir()
    (registry / "bazel_registry.json").write_text("{}\n")
    lines = ['module(name="graph_fixture")']
    for name, version in {**BUILTINS, "alpha": "1", "beta": "1"}.items():
        directory = root / "stubs" / name
        directory.mkdir(parents=True)
        module = f'module(name={name!r},version={version!r})\n'
        if name in ("alpha", "beta"):
            module += f'bazel_dep(name="leaf",version={"1" if name == "alpha" else "2"!r})\n'
        (directory / "MODULE.bazel").write_text(module)
        (directory / "BUILD.bazel").write_text('exports_files(["MODULE.bazel"])\n')
        lines += [f'bazel_dep(name={name!r},version={version!r})',
                  f'local_path_override(module_name={name!r},path={str(directory)!r})']
    for version in ("1", "2", "3"):
        directory = registry / "modules/leaf" / version
        directory.mkdir(parents=True)
        (directory / "MODULE.bazel").write_text(f'module(name="leaf",version={version!r})\n')
        archive = directory / "source.tar"
        with tarfile.open(archive, "w") as output:
            for name, content in {"MODULE.bazel": (directory / "MODULE.bazel").read_bytes(),
                                  "BUILD.bazel": b'exports_files(["MODULE.bazel"])\n'}.items():
                member = tarfile.TarInfo(name)
                member.size = len(content)
                output.addfile(member, io.BytesIO(content))
        (directory / "source.json").write_text(json.dumps({
            "url": archive.as_uri(), "integrity": "sha256-" + base64.b64encode(
                hashlib.sha256(archive.read_bytes()).digest()).decode(),
        }))
    for name, path, symbol, repos in (
        ("rules_java", "java/extensions.bzl", "toolchains", ["local_jdk", "remote_java_tools",
         "remote_java_tools_linux", "remote_java_tools_windows", "remote_java_tools_darwin_x86_64",
         "remote_java_tools_darwin_arm64"]),
        ("buildozer", "buildozer_binary.bzl", "buildozer_binary", ["buildozer_binary"]),
    ):
        path = root / "stubs" / name / path
        path.parent.mkdir(exist_ok=True)
        (path.parent / "BUILD.bazel").touch()
        path.write_text('def _repo(ctx):\n    ctx.file("BUILD.bazel", "")\n'
                        '_repo_rule=repository_rule(implementation=_repo)\n'
                        f'def _ext(ctx):\n    for name in {repos!r}:\n        _repo_rule(name=name)\n'
                        f'{symbol}=module_extension(implementation=_ext)\n')
    lines += ['bad=use_extension("//:extension.bzl","bad")', 'use_repo(bad,"unused_repo")']
    (root / "MODULE.bazel").write_text("\n".join(lines) + "\n")
    (root / "BUILD.bazel").write_text(
        'platform(name="fixture_platform")\nfilegroup(name="good",srcs=["payload"])\n'
        'filegroup(name="requires_extension",srcs=["@unused_repo//:payload"])\n')
    (root / "payload").write_text("original payload\n")
    (root / "extension.bzl").write_text(
        'def _impl(ctx):\n    fail("UNUSED_EXTENSION_SENTINEL")\n'
        'bad=module_extension(implementation=_impl)\n')
    return registry


@unittest.skipUnless(os.environ.get("REGISTRY_CI_TEST_BAZEL"), "Set REGISTRY_CI_TEST_BAZEL for real Bazel")
class BazelModuleGraphTest(unittest.TestCase):
    def test_unused_extension_does_not_block_resolution_or_hide_required_extension_failures(self):
        with tempfile.TemporaryDirectory(prefix="registry-module-graph-") as temporary:
            work = Path(temporary)
            consumer, artifacts = work / "consumer", work / "artifacts"
            consumer.mkdir()
            artifacts.mkdir()
            registry = write_fixture(consumer)
            prefix = [os.environ["REGISTRY_CI_TEST_BAZEL"], "--batch", "--ignore_all_rc_files",
                      "--host_jvm_args=-Xmx512m", "--host_jvm_args=-XX:ActiveProcessorCount=1",
                      "--output_user_root=" + str(work / "bazel")]
            flags = ["--registry=" + registry.as_uri(), "--lockfile_mode=off"]

            def graph(name):
                # The production helper owns failure classification and receipts.
                return cross.module_graph(prefix, flags, consumer, artifacts, name)

            def build(name, target):
                command = [*prefix, "build", *flags, target, "--incompatible_autoload_externally=",
                           "--host_platform=//:fixture_platform", "--platforms=//:fixture_platform",
                           "--jobs=1", "--loading_phase_threads=1", "--remote_cache=", "--disk_cache="]
                (artifacts / (name + "-command.json")).write_text(json.dumps(command, indent=2) + "\n")
                with (artifacts / (name + ".log")).open("w") as log:
                    result = subprocess.run(command, cwd=consumer, stdout=log, stderr=subprocess.STDOUT,
                                            timeout=120)
                return result.returncode, (artifacts / (name + ".log")).read_text()

            try:
                versions = graph("unused-extension")
                self.assertEqual(versions["leaf"], "2")  # Real MVS: alpha wants 1, beta wants 2.
                status = json.loads((artifacts / "unused-extension-status.json").read_text())
                self.assertEqual(status["returncode"], 2)  # Original check=True rejected this.
                self.assertTrue(status["module_resolution_complete"])
                self.assertFalse(status["extension_inspection_complete"])
                self.assertIn("UNUSED_EXTENSION_SENTINEL", (artifacts / "unused-extension.stderr").read_text())
                code, log = build("unrelated-build", "//:good")
                self.assertEqual(code, 0, log)
                code, log = build("required-extension-build", "//:requires_extension")
                self.assertNotEqual(code, 0, log)
                self.assertIn("UNUSED_EXTENSION_SENTINEL", log)

                (artifacts / "failing-extension.bzl").write_bytes((consumer / "extension.bzl").read_bytes())
                (consumer / "extension.bzl").write_text(
                    'def _repo(ctx):\n    ctx.file("BUILD.bazel", "exports_files([\\\"payload\\\"])\\n")\n'
                    '    ctx.file("payload", "generated payload")\n'
                    '_repo_rule=repository_rule(implementation=_repo)\n'
                    'def _impl(ctx):\n    _repo_rule(name="unused_repo")\n'
                    'bad=module_extension(implementation=_impl)\n')
                self.assertEqual(graph("healthy-extension"), versions)
                self.assertEqual(json.loads((artifacts / "healthy-extension-status.json").read_text())[
                    "returncode"], 0)
                code, log = build("healthy-required-build", "//:requires_extension")
                self.assertEqual(code, 0, log)

                module = consumer / "MODULE.bazel"
                original = module.read_text()
                module.write_text(original + '\nbazel_dep(name="leaf",version="3")\n')
                changed = graph("changed-version")
                self.assertEqual(changed["leaf"], "3")
                self.assertNotEqual(changed, versions)
                module.write_text(original + '\nbazel_dep(name="missing_module",version="1")\n')
                with self.assertRaises(subprocess.CalledProcessError):
                    graph("resolution-failure")
                self.assertFalse(json.loads((artifacts / "resolution-failure-status.json").read_text())[
                    "module_resolution_complete"])
                (artifacts / "result.json").write_text(json.dumps({
                    "unused_extension_inspection_rejected_by_original_cli": True,
                    "resolved_versions_equal_with_healthy_extension": True,
                    "original_build_succeeds_without_unused_extension": True,
                    "required_extension_error_still_fails_build": True,
                    "real_mvs_and_graph_drift_observed": True,
                    "module_resolution_errors_remain_fatal": True,
                    "compiler_or_arm_sdk_used": False,
                }, indent=2) + "\n")
            finally:
                shutil.copytree(consumer, artifacts / "inputs", ignore=shutil.ignore_patterns("bazel-*"))
                destination = os.environ.get("REGISTRY_CI_TEST_ARTIFACTS")
                if destination:
                    shutil.copytree(artifacts, Path(destination) / work.name)


if __name__ == "__main__":
    unittest.main()
