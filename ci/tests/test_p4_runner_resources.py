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

    def test_frontends_are_counted_only_in_the_jobs_cgroup(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = Path(tmp)
            samples = [("cc1plus", "/pod/job"), ("cc1", "/pod/job/sandbox"), ("cc1", "/pod/job2"), ("java", "/pod/job")]
            for pid, (name, group) in enumerate(samples, start=1):
                process = proc / str(pid)
                process.mkdir()
                (process / "cgroup").write_text("0::" + group + "\n")
                (process / "comm").write_text(name + "\n")
            self.assertEqual(resources.gcc_frontends(proc, "/pod/job"), 2)

    def test_large_job_verifies_capacity_and_preserves_child_result(self):
        actual = {"cpu_quota_cores": 8, "cpu_affinity_count": 16, "memory_limit_bytes": 16 * 1024**3}
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(resources, "unified_cgroup", return_value="/runner"), \
                mock.patch.object(resources, "gcc_frontends", return_value=3):
            output = Path(tmp) / "receipt.json"
            with mock.patch.object(resources, "capacity", return_value=actual):
                self.assertEqual(resources.monitor(output, [sys.executable, "-c", "raise SystemExit(23)"]), 23)
            receipt = json.loads(output.read_text())
            self.assertEqual((receipt["exit_code"], receipt["peak_observed_gcc_frontends"]), (23, 3))
            for mismatch in ({"memory_limit_bytes": 6 * 1024**3}, {"cpu_quota_cores": 6}, {"cpu_affinity_count": 4}):
                with self.subTest(mismatch=mismatch), \
                        mock.patch.object(resources, "capacity", return_value={**actual, **mismatch}), \
                        mock.patch.object(resources.subprocess, "Popen") as child:
                    with self.assertRaisesRegex(ValueError, "8 CPU / 16 GiB"):
                        resources.monitor(output, ["not-started"])
                    child.assert_not_called()


if __name__ == "__main__":
    unittest.main()
