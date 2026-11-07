#!/usr/bin/env python3
"""Exercise the acceptance driver using recorded commands, never real Bazel."""

import contextlib
import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

SPEC = importlib.util.spec_from_file_location("verify_rebuild", Path(__file__).with_name("verify_rebuild.py"))
VERIFY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFY)

# Actual Bazel 8.5.1 baseline event from accepted buildimage233b AMD64 CI
# (job127024306523); protobuf JSON omits the default numeric exit code.
ACCEPTED_FINISHED = {
    "id": {"buildFinished": {}},
    "children": [{"buildToolLogs": {}}, {"buildMetrics": {}}],
    "finished": {"overallSuccess": True, "finishTimeMillis": "1793849962427",
                 "exitCode": {"name": "SUCCESS"}, "finishTime": "2026-11-05T03:39:22.427Z"},
}


class BuildEventTest(unittest.TestCase):
    def check(self, event):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "events.json"
            path.write_text(json.dumps(event) + "\n")
            VERIFY.successful_events(path)

    def test_actual_success_event_with_omitted_or_explicit_zero(self):
        self.check(ACCEPTED_FINISHED)
        explicit = copy.deepcopy(ACCEPTED_FINISHED)
        explicit["finished"]["exitCode"]["code"] = 0
        self.check(explicit)

    def test_rejects_missing_failed_or_contradictory_success_fields(self):
        for finished in (
            {}, {"overallSuccess": True},
            {"exitCode": {"name": "SUCCESS"}},
            {"overallSuccess": False, "exitCode": {"name": "SUCCESS"}},
            {"overallSuccess": True, "exitCode": {"code": 0}},
            {"overallSuccess": True, "exitCode": {"name": "BUILD_FAILURE", "code": 0}},
            {"overallSuccess": True, "exitCode": {"name": "SUCCESS", "code": 1}},
            {"overallSuccess": True, "exitCode": {"name": "SUCCESS", "code": False}},
        ):
            with self.subTest(finished=finished), self.assertRaises(ValueError):
                self.check({"id": {"buildFinished": {}}, "finished": finished})


class RebuildTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.output_base = self.root / "output base with spaces"
        self.execution = self.output_base / "execroot/_main"
        self.owner = self.execution / "external/libteam+"
        (self.owner / "bazel").mkdir(parents=True)
        self.script = self.owner / "bazel/verify_rebuild.py"
        self.script.write_bytes(Path(VERIFY.__file__).read_bytes())
        self.config = self.owner / "bazel/config.h.in"
        self.original = b"/* owner config */\n" + VERIFY.NEEDLE + b"\n#define ENABLE_DBUS 1\n"
        self.config.write_bytes(self.original)
        for name in ("MODULE.bazel", "BUILD.bazel"):
            (self.owner / name).write_text("# fixture " + name + "\n")
        self.consumer = self.root / "consumer"
        self.consumer.mkdir()
        self.decoy = self.consumer / "config.h.in"
        self.decoy.write_bytes(self.original)
        self.lock_entry = "https://registry.example/revision/modules/libteam/1.31.0.sonic.1/source.json"
        (self.consumer / "MODULE.bazel.lock").write_text(json.dumps({
            "registryFileHashes": {self.lock_entry: "abc", "https://other/modules/other/1/source.json": "def"}}))
        self.output = self.consumer / "artifacts/rebuild"
        names = (
            "libteam_runtime_amd64_rttar.tar", "libteam_runtime_amd64.debug_symbols.tar",
            "libteamdctl_runtime_amd64_rttar.tar", "libteamdctl_runtime_amd64.debug_symbols.tar",
            "libteam_utils_runtime_rttar.tar", "libteam_utils_runtime.debug_symbols.tar",
            "libteam_dev_amd64.tar", "runtime_packages.json", "library_runtime_packages.json",
        )
        self.paths = [Path("bazel-out/k8-fastbuild/bin/external/libteam+") / name for name in names]
        self.calls = []
        self.configs = []
        self.phase = None
        self.problem = None
        self.flags = ["--host_platform=@sonic_build_infra//platforms:x86_64_trixie",
                      "--platforms=@sonic_build_infra//platforms:x86_64_trixie",
                      "--experimental_downloader_config=/cache/downloader.cfg",
                      "--repository_cache=/cache/repos", "--disk_cache=/cache/actions", "--jobs=7"]

    def fake_bazel(self, command, **options):
        self.calls.append(command)
        self.assertEqual(command[0], "existing_bazel_wrapper")
        self.assertTrue(options["check"])
        operation = command[1]
        self.assertIn(operation, ("info", "cquery", "build"))
        if operation == "info":
            self.assertEqual(command[2:], self.flags + ["output_base"])
            value = str(self.output_base) + "\n"
            if isinstance(self.problem, tuple) and self.problem[0] == "output-base":
                value = self.problem[1]
            return subprocess.CompletedProcess(command, 0, value)
        if operation == "cquery":
            self.assertEqual(command[2:2 + len(self.flags)], self.flags)
            if command[-2] == VERIFY.SCRIPT_LABEL:
                source = "external/libteam+/bazel/verify_rebuild.py"
                if self.problem == "wrong-owner":
                    source = str(self.consumer / "verify_rebuild.py")
                return subprocess.CompletedProcess(command, 0, source + "\n")
            self.assertEqual(command[-2], "set(" + " ".join("@libteam//:" + name for name in VERIFY.OUTPUTS) + ")")
            self.assertEqual(command[-1], "--output=files")
            if self.problem == (self.phase, "query-failure"):
                raise subprocess.CalledProcessError(1, command)
            paths = list(self.paths)
            if self.problem == (self.phase, "duplicate-output"):
                paths[-1] = paths[0]
            if self.problem == (self.phase, "too-few-outputs"):
                paths.pop()
            if self.problem == (self.phase, "changed-output-set"):
                changed = paths[0].with_name("other.tar")
                (self.execution / changed).write_bytes(b"unexpected output")
                paths[0] = changed
            return subprocess.CompletedProcess(command, 0, "\n".join(map(str, paths)) + "\n")
        self.assertEqual(command[2:3 + len(self.flags)], ["--jobs=2"] + self.flags)
        self.assertEqual(command[-9:], ["@libteam//:" + name for name in VERIFY.OUTPUTS])
        events = Path(next(arg.split("=", 1)[1] for arg in command if arg.startswith("--build_event_json_file=")))
        self.phase = events.name.removesuffix("-events.json")
        self.configs.append((self.phase, self.config.read_bytes()))
        if self.problem == (self.phase, "build-failure"):
            raise subprocess.CalledProcessError(1, command)
        if self.problem != (self.phase, "missing-events"):
            payload = json.dumps(ACCEPTED_FINISHED) + "\n"
            if self.problem == (self.phase, "empty-events"):
                payload = ""
            if self.problem == (self.phase, "failed-events"):
                payload = payload.replace('"name": "SUCCESS"', '"name": "BUILD_FAILURE", "code": 1')
            if self.problem == (self.phase, "unfinished-events"):
                payload = '{"started": {"command": "build"}}\n'
            if self.problem == (self.phase, "invalid-events"):
                payload = "not json\n"
            events.write_text(payload)
        edited = self.config.read_bytes() != self.original
        for relative in self.paths:
            path = self.execution / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            variable = "libteam_utils_runtime" in path.name or path.name == "runtime_packages.json"
            changed = edited and variable and self.problem != "inert-edit"
            if self.problem == "unrelated-edit" and edited and path.name == "library_runtime_packages.json":
                changed = True
            if self.problem == (self.phase, "changed-output"):
                changed = True
            path.write_bytes((path.name + (" changed" if changed else " baseline")).encode())
        if self.problem == (self.phase, "missing-output"):
            (self.execution / self.paths[0]).unlink()
        if self.problem == (self.phase, "changed-source"):
            (self.owner / "MODULE.bazel").write_text("changed module\n")
        return subprocess.CompletedProcess(command, 0)

    def run_probe(self):
        previous = Path.cwd()
        with contextlib.ExitStack() as stack:
            stack.callback(os.chdir, previous)
            os.chdir(self.consumer)
            stack.enter_context(mock.patch.object(VERIFY, "__file__", str(self.script)))
            stack.enter_context(mock.patch.object(VERIFY.subprocess, "run", side_effect=self.fake_bazel))
            VERIFY.main(["--bazel", "existing_bazel_wrapper", "--output", str(self.output),
                         *["--bazel-arg=" + flag for flag in self.flags]])

    def receipt(self):
        return json.loads((self.output / "rebuild.json").read_text())

    def assert_restored(self):
        self.assertEqual(self.config.read_bytes(), self.original)
        self.assertEqual(self.decoy.read_bytes(), self.original)
        self.assertTrue(self.receipt()["source_restored"])

    def test_four_phases_owner_binding_flags_and_evidence(self):
        self.run_probe()
        receipt = self.receipt()
        self.assertEqual(receipt["status"], "passed")
        self.assert_restored()
        self.assertEqual([phase for phase, _ in self.configs], ["baseline", "no-op", "config-edit", "restored"])
        self.assertEqual([contents for _, contents in self.configs],
                         [self.original, self.original, self.original.replace(VERIFY.NEEDLE, VERIFY.EDIT), self.original])
        builds = receipt["builds"]
        self.assertEqual(builds[0]["outputs_sha256"], builds[1]["outputs_sha256"])
        self.assertEqual(builds[0]["outputs_sha256"], builds[3]["outputs_sha256"])
        self.assertNotEqual(builds[0]["outputs_sha256"], builds[2]["outputs_sha256"])
        self.assertEqual(receipt["owner_root"], str(self.owner))
        self.assertEqual(receipt["execution_root"], str(self.execution))
        self.assertEqual(receipt["bazel_arguments"], self.flags)
        self.assertEqual(receipt["commands"], self.calls)
        self.assertEqual(receipt["observed_registry_files"], {self.lock_entry: "abc"})
        for source, digest in receipt["owner_source_sha256"].items():
            self.assertEqual(digest, VERIFY.sha(self.owner / source))
        for build in builds:
            self.assertEqual(len(build["outputs_sha256"]), 9)
            self.assertEqual(build["events_sha256"], VERIFY.sha(self.output / build["events"]))
        self.assertIn("no zero-action", receipt["scope"])
        self.assertEqual(len(self.calls), 10)

    def test_rejects_invalid_or_missing_standard_execution_root_before_query(self):
        for value in ("", "relative/base\n", str(self.root / "missing") + "\n",
                      str(self.output_base) + "\n" + str(self.output_base) + "\n"):
            with self.subTest(value=value):
                self.calls.clear()
                self.problem = ("output-base", value)
                with self.assertRaises(ValueError):
                    self.run_probe()
                self.assertEqual(len(self.calls), 1)
                self.assertEqual(self.calls[0][1], "info")
                self.assertEqual(self.configs, [])
                self.assert_restored()
                self.assertEqual(self.receipt()["status"], "failed")

    def test_rejects_wrong_owner_before_build(self):
        self.problem = "wrong-owner"
        with self.assertRaisesRegex(ValueError, "selected @libteam owner script"):
            self.run_probe()
        self.assertEqual(self.configs, [])
        self.assert_restored()

    def test_rejects_commented_duplicated_or_already_edited_input(self):
        self.output.mkdir(parents=True, exist_ok=True)
        receipt = self.output / "rebuild.json"
        for contents in (self.original.replace(VERIFY.NEEDLE, b"// " + VERIFY.NEEDLE),
                         VERIFY.NEEDLE + b"\n" + self.original,
                         self.original.replace(VERIFY.NEEDLE, VERIFY.EDIT)):
            receipt.write_text('{"status": "passed"}\n')
            self.config.write_bytes(contents)
            with self.assertRaisesRegex(ValueError, "reviewed PACKAGE_VERSION input"):
                self.run_probe()
            self.assertEqual(self.config.read_bytes(), contents)
            self.assertFalse(receipt.exists())
        self.config.write_bytes(self.original)
        for path in (self.config, self.owner / "MODULE.bazel", self.owner / "BUILD.bazel", self.script):
            with self.subTest(missing=path):
                contents = path.read_bytes()
                receipt.write_text('{"status": "passed"}\n')
                path.unlink()
                try:
                    with self.assertRaises(FileNotFoundError):
                        self.run_probe()
                finally:
                    path.write_bytes(contents)
                self.assertFalse(receipt.exists())
        self.assertEqual(self.calls, [])

    def test_rejects_inert_and_unrelated_edits(self):
        for problem, message in (("inert-edit", "did not invalidate"), ("unrelated-edit", "unrelated owner output")):
            with self.subTest(problem=problem):
                self.problem = problem
                with self.assertRaisesRegex(ValueError, message):
                    self.run_probe()
                self.assert_restored()
                self.assertEqual(self.receipt()["status"], "failed")

    def test_restores_on_build_and_query_failure_in_every_phase(self):
        for phase in ("baseline", "no-op", "config-edit", "restored"):
            for failure in ("build-failure", "query-failure"):
                with self.subTest(phase=phase, failure=failure):
                    self.problem = (phase, failure)
                    with self.assertRaises(subprocess.CalledProcessError):
                        self.run_probe()
                    self.assert_restored()
                    self.assertEqual(self.receipt()["status"], "failed")

    def test_rejects_missing_duplicate_or_changed_outputs(self):
        for problem in ("missing-output", "duplicate-output", "too-few-outputs", "changed-output-set"):
            with self.subTest(problem=problem):
                self.problem = ("config-edit", problem)
                with self.assertRaises(ValueError):
                    self.run_probe()
                self.assert_restored()

    def test_rejects_missing_empty_failed_or_incomplete_events(self):
        for problem in ("missing-events", "empty-events", "failed-events", "unfinished-events", "invalid-events"):
            with self.subTest(problem=problem):
                self.problem = ("config-edit", problem)
                self.output.mkdir(parents=True, exist_ok=True)
                # A stale successful event may not satisfy the next run.
                (self.output / "config-edit-events.json").write_text(
                    json.dumps(ACCEPTED_FINISHED) + "\n")
                with self.assertRaises(ValueError):
                    self.run_probe()
                self.assert_restored()

    def test_rejects_noop_or_restoration_mismatch(self):
        for phase in ("no-op", "restored"):
            with self.subTest(phase=phase):
                self.problem = (phase, "changed-output")
                with self.assertRaisesRegex(ValueError, "outputs"):
                    self.run_probe()
                self.assert_restored()

    def test_rejects_other_owner_source_changes(self):
        self.problem = ("restored", "changed-source")
        with self.assertRaisesRegex(ValueError, "owner source changed"):
            self.run_probe()
        self.assert_restored()
        self.assertEqual(self.receipt()["status"], "failed")


if __name__ == "__main__":
    unittest.main()
