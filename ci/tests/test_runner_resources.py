"""Runner capacity, action telemetry and unchanged command execution."""

import importlib.util
import json
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

    def test_memory_budget_reserves_heap_and_system_headroom(self):
        with mock.patch.object(resources.os, "sysconf", side_effect=lambda key:
                               {"SC_PHYS_PAGES": 32 * 1024**3 // 4096, "SC_PAGE_SIZE": 4096}[key]):
            for gib, expected in ((6, 3276), (16, 11468), (64, 24576), (None, 24576)):
                with self.subTest(gib=gib):
                    self.assertEqual(resources.action_memory_mb({"memory_limit_bytes":
                        gib * 1024**3 if gib is not None else None}), expected)
            with self.assertRaisesRegex(ValueError, "JVM heap reserve"):
                resources.action_memory_mb({"memory_limit_bytes": 2048 * 1024**2})

    def test_expensive_compilers_have_module_specific_job_caps(self):
        limits = {"cpu_quota_cores": 8, "memory_limit_bytes": 16 * 1024**3}
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(resources, "capacity", return_value=limits), \
                mock.patch.object(resources, "unified_cgroup", return_value="/runner"), \
                mock.patch.object(resources.subprocess, "run", return_value=mock.Mock(returncode=0)) as child:
            receipt = Path(tmp) / "receipt.json"
            for module, arch, jobs in (("p4c", "arm64", 3), ("sonic-dash", "amd64", 3),
                                       ("sonic-swss", "amd64", 2), ("sonic-swss", "arm64", 1),
                                       ("libnl3", "arm64", None)):
                with self.subTest(module=module, architecture=arch):
                    self.assertEqual(resources.run(receipt, ["registry-ci"], module, arch), 0)
                    args = child.call_args.args[0]
                    job_flags = [arg for arg in args if arg.startswith("--bazel-build-arg=--jobs=")]
                    self.assertEqual(job_flags, [f"--bazel-build-arg=--jobs={jobs}"] if jobs else [])
                    self.assertEqual(json.loads(receipt.read_text()).get("bazel_jobs"), jobs)

    def test_monitor_adds_memory_budget_and_preserves_child_failure(self):
        limits = {"cpu_quota_cores": 3, "cpu_affinity_count": 16, "memory_limit_bytes": 8 * 1024**3}
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(resources, "unified_cgroup", return_value="/runner"):
            output = Path(tmp) / "receipt.json"
            capture = Path(tmp) / "arguments.json"
            command = [sys.executable, "-c", "import json,sys; "
                       "open(sys.argv[1], 'w').write(json.dumps(sys.argv[2:])); raise SystemExit(23)", str(capture), "--caller-option=value with spaces"]
            with mock.patch.object(resources, "capacity", return_value=limits):
                self.assertEqual(resources.run(output, command), 23)
            arguments = json.loads(capture.read_text())
            self.assertEqual(arguments, ["--caller-option=value with spaces",
                "--bazel-build-arg=--local_resources=memory=4915"])
            receipt = json.loads(output.read_text())
            self.assertEqual(receipt["exit_code"], 23)
            self.assertEqual(receipt["cpu_quota_cores"], 3)
            self.assertEqual(receipt["memory_limit_bytes"], 8 * 1024**3)
            self.assertEqual(receipt["build_cpu"]["build"], {"status": "missing_metrics"})


if __name__ == "__main__":
    unittest.main()
