"""Resource limits and build status on large P4 runners."""

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


path = Path(__file__).resolve().parents[1] / "p4_runner_resources.py"
spec = importlib.util.spec_from_file_location("p4_runner_resources", path)
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
                   "actionData": [tracked, unmeasured, {**tracked, "mnemonic": "CppCompile"}]}
        with tempfile.TemporaryDirectory() as tmp:
            events = Path(tmp) / "build-events.jsonl"
            events.write_text(json.dumps({"buildMetrics": {"actionSummary": summary}}) + "\n")
            self.assertEqual(resources.foreign_cpu(events),
                             {"status": "reported", "groups": [
                                 {"mnemonic": "CcCmakeMakeRule", "reported_actions": 2, "cpu_seconds": 7.5,
                                  "elapsed_span_seconds": 2.5, "average_cores": 3.0},
                                 {"mnemonic": "CcConfigureMakeRule", "reported_actions": 3}]})

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
            result = resources.local_foreign_cpu({"runnerCount": runners, "actionData": [group]})
            self.assertEqual(result["status"], status)
            self.assertNotIn("average_cores", json.dumps(result))
        with tempfile.TemporaryDirectory() as tmp:
            events = Path(tmp) / "test-events.jsonl"
            self.assertEqual(resources.foreign_cpu(events), {"status": "missing_metrics"})
            events.write_text('{"buildMetrics":')
            self.assertEqual(resources.foreign_cpu(events), {"status": "missing_metrics"})

    def test_large_job_verifies_capacity_and_preserves_child_result(self):
        actual = {"cpu_quota_cores": 8, "cpu_affinity_count": 16, "memory_limit_bytes": 16 * 1024**3}
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(resources, "unified_cgroup", return_value="/runner"):
            output = Path(tmp) / "receipt.json"
            with mock.patch.object(resources, "capacity", return_value=actual):
                self.assertEqual(resources.run(output, [sys.executable, "-c", "raise SystemExit(23)"]), 23)
            receipt = json.loads(output.read_text())
            self.assertEqual(receipt["exit_code"], 23)
            self.assertEqual(receipt["foreign_build_cpu"]["build"], {"status": "missing_metrics"})
            for mismatch in ({"memory_limit_bytes": 6 * 1024**3}, {"cpu_quota_cores": 6}, {"cpu_affinity_count": 4}):
                with self.subTest(mismatch=mismatch), \
                        mock.patch.object(resources, "capacity", return_value={**actual, **mismatch}), \
                        mock.patch.object(resources.subprocess, "run") as child:
                    with self.assertRaisesRegex(ValueError, "8 CPU / 16 GiB"):
                        resources.run(output, ["not-started"])
                    child.assert_not_called()


if __name__ == "__main__":
    unittest.main()
