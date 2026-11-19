"""Retain distinct, readable profiles from actual Bazel build/test commands."""

import gzip
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("registry_profile_fixture", Path(__file__).resolve().parents[1] / "registry_ci.py")
registry_ci = importlib.util.module_from_spec(spec)
spec.loader.exec_module(registry_ci)


@unittest.skipUnless(os.environ.get("REGISTRY_CI_TEST_BAZEL"), "requires the real Bazel profile fixture")
class AnalysisProfileTest(unittest.TestCase):
    def test_both_commands_retain_trace_cpu_and_gc_evidence(self):
        with tempfile.TemporaryDirectory(prefix="registry-analysis-profile-") as temporary:
            root = Path(temporary)
            artifacts = root / "artifacts"
            artifacts.mkdir()
            (root / "MODULE.bazel").write_text('module(name="profile_fixture")\n')
            (root / "BUILD.bazel").write_text('load(":probe.bzl", "probe_test")\nprobe_test(name="payload")\n')
            (root / "probe.bzl").write_text(
                'def _impl(ctx):\n'
                '    ctx.actions.write(ctx.outputs.executable, "#!/bin/sh\\nexit 0\\n", is_executable=True)\n'
                '    return [DefaultInfo(executable=ctx.outputs.executable)]\n'
                'probe_test=rule(implementation=_impl, test=True)\n')
            prefix = [os.environ["REGISTRY_CI_TEST_BAZEL"], "--ignore_all_rc_files",
                      "--output_user_root=" + str(root / "bazel"),
                      *registry_ci.analysis_profile_startup_args(artifacts)]
            try:
                for phase in ("build", "test"):
                    registry_ci.run_logged([*prefix, phase, *registry_ci.analysis_profile_flags(artifacts, phase),
                                            "//:payload"], root, artifacts / (phase + ".log"))
                    trace = json.loads((artifacts / (phase + ".profile.json")).read_text())
                    self.assertTrue(trace["traceEvents"])
                    with gzip.open(artifacts / (phase + ".starlark.pprof"), "rb") as stream:
                        self.assertTrue(stream.read())
                self.assertTrue((artifacts / "jvm-gc.log").stat().st_size)
            finally:
                subprocess.run([*prefix, "shutdown"], cwd=root, check=True, capture_output=True)
