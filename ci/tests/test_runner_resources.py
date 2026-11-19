"""Runner-derived budgets, action telemetry and build status."""

import importlib.util
import json
import os
import subprocess
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


path = Path(__file__).resolve().parents[1] / "runner_resources.py"
spec = importlib.util.spec_from_file_location("runner_resources", path)
assert spec is not None and spec.loader is not None
resources = importlib.util.module_from_spec(spec)
spec.loader.exec_module(resources)


class ResourceTests(unittest.TestCase):
    def test_capacity_uses_effective_pod_and_container_limits(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pod = root / "pod"
            runner = pod / "runner"
            runner.mkdir(parents=True)
            (pod / "cpu.max").write_text("800000 100000\n")
            (runner / "cpu.max").write_text("max 100000\n")
            (pod / "memory.max").write_text(str(16 * 1024**3))
            (runner / "memory.max").write_text("max\n")
            self.assertEqual(resources.capacity("/pod/runner", root)["cpu_quota_cores"], 8)
            self.assertEqual(resources.capacity("/pod/runner", root)["memory_limit_bytes"], 16 * 1024**3)
            (runner / "cpu.max").write_text("600000 100000\n")
            self.assertEqual(resources.capacity("/pod/runner", root)["cpu_quota_cores"], 6)

    def test_memory_receipt_reports_supported_cgroup_events_and_peak(self):
        with tempfile.TemporaryDirectory() as tmp:
            group = Path(tmp)
            self.assertEqual(resources.memory_usage(group), {})
            (group / "memory.peak").write_text("123456\n")
            (group / "memory.events").write_text("low 0\nhigh 0\nmax 2\noom 1\noom_kill 1\n")
            self.assertEqual(resources.memory_usage(group),
                             {"peak_bytes": 123456, "events": {"max": 2, "oom": 1, "oom_kill": 1}})

    def test_foreign_group_cpu_uses_measured_duration_across_multiple_actions(self):
        tracked = {"mnemonic": "CcCmakeMakeRule", "actionsExecuted": "2",
                   "firstStartedMs": "1000", "lastEndedMs": "3500", "userTime": "6.000s", "systemTime": "1.500s"}
        unmeasured = {"mnemonic": "CcConfigureMakeRule", "actionsExecuted": "3"}
        summary = {"runnerCount": [{"name": "linux-sandbox", "count": 2, "execKind": "Local"},
                                   {"name": "remote cache hit", "count": 5, "execKind": "Remote"}],
                   "actionData": [tracked, unmeasured, {"mnemonic": "CppCompile", "actionsExecuted": "5"}]}
        with tempfile.TemporaryDirectory() as tmp:
            events = Path(tmp) / "build-events.jsonl"
            events.write_text(json.dumps({"buildMetrics": {"actionSummary": summary}}) + "\n")
            self.assertEqual(resources.action_cpu(events),
                             {"status": "reported", "groups": [
                                 {"mnemonic": "CcCmakeMakeRule", "reported_actions": 2, "cpu_seconds": 7.5,
                                  "elapsed_span_seconds": 2.5, "average_cores": 3.0},
                                 {"mnemonic": "CcConfigureMakeRule", "reported_actions": 3},
                                 {"mnemonic": "CppCompile", "reported_actions": 5}]})

    def test_remote_cache_only_remote_execution_and_missing_events_have_no_estimate(self):
        local = {"name": "linux-sandbox", "count": 1, "execKind": "Local"}
        cache = {"name": "remote cache hit", "count": 1, "execKind": "Remote"}
        remote = {"name": "remote", "count": 1, "execKind": "Remote"}
        action = {"mnemonic": "CcMakeRule", "actionsExecuted": "1", "userTime": "3.2s",
                  "firstStartedMs": "4000", "lastEndedMs": "5000"}
        for runners, group, status in (([cache], action, "no_local_execution"),
                                       ([local, remote], action, "unattributed_execution"),
                                       ([local, {**local, "name": "deduplicated"}], action, "unattributed_execution"),
                                       ([local], {**action, "userTime": "0s"}, "no_cpu_measurement"),
                                       ([local], {**action, "lastEndedMs": "4000"}, "no_cpu_measurement")):
            result = resources.local_action_cpu({"runnerCount": runners, "actionData": [group]})
            self.assertEqual(result["status"], status)
            self.assertNotIn("average_cores", json.dumps(result))
        with tempfile.TemporaryDirectory() as tmp:
            events = Path(tmp) / "test-events.jsonl"
            self.assertEqual(resources.action_cpu(events), {"status": "missing_metrics"})
            events.write_text('{"buildMetrics":')
            self.assertEqual(resources.action_cpu(events), {"status": "missing_metrics"})

    def test_budget_follows_quota_affinity_memory_and_heap(self):
        cases = (
            (1.5, 16, 6, 2048, 2, 1.5, 3276),
            (8, 16, 16, 2048, 8, 8, 11468),
            (24, 4, 32, 1024, 4, 4, 25395),
            (None, 12, None, 2048, 12, 12, 50790),
        )
        # The host has 64 GiB; finite cgroup limits remain authoritative.
        with mock.patch.object(resources.os, "sysconf", side_effect=lambda key: {
                "SC_PHYS_PAGES": 64 * 1024**3 // 4096, "SC_PAGE_SIZE": 4096}[key]):
            for quota, affinity, gib, heap, jobs, cpu, memory in cases:
                with self.subTest(quota=quota, affinity=affinity, gib=gib, heap=heap):
                    actual = resources.action_budget({"cpu_quota_cores": quota,
                        "cpu_affinity_count": affinity,
                        "memory_limit_bytes": gib * 1024**3 if gib else None}, heap)
                    self.assertEqual(actual, {"jobs": jobs, "cpu": cpu,
                                             "memory_mb": memory, "jvm_heap_mb": heap})
            self.assertEqual(resources.action_budget({"cpu_quota_cores": 96,
                "cpu_affinity_count": 96, "memory_limit_bytes": 128 * 1024**3}, 2048)["memory_mb"], 50790)

    def test_insufficient_memory_or_cpu_fails_before_execution(self):
        for cpu, memory in ((0, 6 * 1024**3), (2, 0), (2, 1024**3), (2, 2 * 1024**3)):
            with self.subTest(cpu=cpu, memory=memory):
                with self.assertRaisesRegex(ValueError, "after the JVM reserve"):
                    resources.action_budget({"cpu_quota_cores": cpu,
                        "cpu_affinity_count": 8, "memory_limit_bytes": memory}, 2048)

    def test_job_passes_the_budget_and_preserves_child_failure(self):
        limits = {"cpu_quota_cores": 3, "cpu_affinity_count": 16, "memory_limit_bytes": 8 * 1024**3}
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(resources, "unified_cgroup", return_value="/runner"):
            output = Path(tmp) / "receipt.json"
            capture = Path(tmp) / "arguments.json"
            command = [sys.executable, "-c", "import json,sys; "
                       "open(sys.argv[1], 'w').write(json.dumps(sys.argv[2:])); raise SystemExit(23)", str(capture)]
            with mock.patch.object(resources, "capacity", return_value=limits):
                self.assertEqual(resources.run(output, command), 23)
            arguments = json.loads(capture.read_text())
            self.assertEqual(arguments, ["--bazel-startup-arg=--host_jvm_args=-Xmx2048m",
                "--bazel-build-arg=--jobs=3", "--bazel-build-arg=--local_resources=cpu=3",
                "--bazel-build-arg=--local_resources=memory=4915",
                "--bazel-build-arg=--experimental_action_resource_set"])
            receipt = json.loads(output.read_text())
            self.assertEqual(receipt["exit_code"], 23)
            self.assertEqual(receipt["bazel_arguments"], arguments)
            self.assertEqual(receipt["build_cpu"]["build"], {"status": "missing_metrics"})


@unittest.skipUnless(os.environ.get("REGISTRY_CI_TEST_BAZEL"),
                     "set REGISTRY_CI_TEST_BAZEL to verify real Bazel resource scheduling")
class BazelResourceSchedulingTest(unittest.TestCase):
    def test_declared_action_cpu_controls_parallelism_with_the_runner_budget(self):
        with tempfile.TemporaryDirectory(prefix="registry-resource-scheduling-") as temporary:
            root = Path(temporary)
            (root / "MODULE.bazel").write_text('module(name="resource_fixture")\n')
            (root / "BUILD.bazel").write_text(
                'load(":actions.bzl", "probe")\n'
                + ''.join(f'probe(name="task{number}", script="record.py")\n' for number in range(4)))
            (root / "actions.bzl").write_text('''
def _resources(os, inputs):
    return {"cpu": 2, "memory": 16}

def _impl(ctx):
    out = ctx.actions.declare_file(ctx.label.name + ".txt")
    ctx.actions.run(
        executable = "/usr/bin/python3",
        inputs = [ctx.file.script],
        outputs = [out],
        arguments = [ctx.file.script.path, ctx.attr.state, out.path],
        resource_set = _resources,
    )
    return [DefaultInfo(files=depset([out]))]

probe = rule(implementation=_impl, attrs={
    "script": attr.label(allow_single_file=True),
    "state": attr.string(default=''' + repr(str(root / "state.json")) + '),\n})\n')
            recorder = '''
import fcntl, json, pathlib, sys, time
state = pathlib.Path(sys.argv[1])
def change(delta):
    with state.with_suffix(".lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        values = json.loads(state.read_text())
        values["active"] += delta
        values["peak"] = max(values["peak"], values["active"])
        state.write_text(json.dumps(values))
change(1)
time.sleep(.5)
pathlib.Path(sys.argv[2]).write_text("built\\n")
change(-1)
'''
            prefix = [os.environ["REGISTRY_CI_TEST_BAZEL"], "--ignore_all_rc_files",
                      "--output_user_root=" + str(root / "bazel")]
            try:
                for cpus, expected_peak in ((2, 1), (4, 2)):
                    with self.subTest(cpus=cpus):
                        # Changing a declared source forces both measured builds to execute.
                        (root / "record.py").write_text(recorder + f"\n# capacity {cpus}\n")
                        (root / "state.json").write_text('{"active":0,"peak":0}')
                        budget = resources.action_budget({"cpu_quota_cores": cpus,
                            "cpu_affinity_count": 8, "memory_limit_bytes": 8 * 1024**3}, 2048)
                        arguments = [f"--jobs={budget['jobs']}",
                                     f"--local_resources=cpu={budget['cpu']}",
                                     f"--local_resources=memory={budget['memory_mb']}",
                                     "--experimental_action_resource_set", "--spawn_strategy=local"]
                        result = subprocess.run([*prefix, "build", *arguments,
                            *[f"//:task{number}" for number in range(4)]], cwd=root, text=True, capture_output=True)
                        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                        self.assertEqual(json.loads((root / "state.json").read_text()),
                                         {"active": 0, "peak": expected_peak})
                        for number in range(4):
                            self.assertEqual((root / f"bazel-bin/task{number}.txt").read_text(), "built\n")
            finally:
                subprocess.run([*prefix, "shutdown"], cwd=root, check=True, capture_output=True)


if __name__ == "__main__":
    unittest.main()
