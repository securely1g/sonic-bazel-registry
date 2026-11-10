"""Check that Bazel exports a writable, per-test HOME to Python subprocesses."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


PROBE = '''#!/usr/bin/env python3
import json
import os
from pathlib import Path

home = os.environ.get("HOME")
temporary = os.environ["TEST_TMPDIR"]
print(json.dumps({"HOME": home, "TEST_TMPDIR": temporary}), flush=True)
assert home == temporary, "HOME must reach Python as the per-test directory"
assert Path.home() == Path(temporary)
assert os.environ["SONIC_TEST_RUNTIME_ID"] == "a" * 64
assert os.environ["REGISTRY_CI_HOME_MARKER"] == "preserved"
config = Path.home() / ".config"
config.mkdir(mode=0o700)
startup = config / "startup.py"
startup.write_text("test configuration")
assert startup.read_text() == "test configuration"
'''


@unittest.skipUnless(os.environ.get("REGISTRY_CI_TEST_BAZEL"),
                     "set REGISTRY_CI_TEST_BAZEL to run the real Bazel test HOME fixture")
class BazelTestHomeIntegrationTest(unittest.TestCase):
    def test_explicit_empty_home_exports_writable_test_directory(self):
        bazel_timeout = 600 if os.environ.get("REGISTRY_CI_EMULATED_ARM") == "true" else 180
        with tempfile.TemporaryDirectory(prefix="registry-bazel-home-") as temporary:
            work = Path(temporary)
            consumer, artifacts = work / "consumer", work / "artifacts"
            consumer.mkdir()
            artifacts.mkdir()
            (consumer / "MODULE.bazel").write_text('module(name = "test_home_fixture")\n')
            (consumer / "BUILD.bazel").write_text(
                'load(":home.bzl", "home_test")\n'
                'platform(name = "fixture_platform")\n'
                'home_test(name = "home")\n')
            (consumer / "home.bzl").write_text(
                'def _impl(ctx):\n'
                '    script = ctx.actions.declare_file(ctx.label.name + ".py")\n'
                f'    ctx.actions.write(script, {json.dumps(PROBE)}, is_executable = True)\n'
                '    return [DefaultInfo(executable = script)]\n'
                'home_test = rule(implementation = _impl, test = True)\n')
            prefix = [os.environ["REGISTRY_CI_TEST_BAZEL"], "--batch", "--ignore_all_rc_files",
                      "--output_user_root=" + str(work / "bazel")]
            flags = ["--incompatible_autoload_externally=", "--lockfile_mode=off",
                     "--host_platform=//:fixture_platform", "--platforms=//:fixture_platform",
                     "--nocache_test_results", "--test_output=all",
                     "--test_env=SONIC_TEST_RUNTIME_ID=" + "a" * 64,
                     "--test_env=REGISTRY_CI_HOME_MARKER=preserved"]
            # No test should rely on the caller's absolute, unwritable home.
            environment = {**os.environ, "HOME": "/proc/registry-ci-unwritable-home"}
            try:
                for case, home_flags, succeeds in (
                        ("absent", [], False),
                        ("unwritable", ["--test_env=HOME=/proc/registry-ci-unwritable-home"], False),
                        ("per-test", ["--test_env=HOME="], True)):
                    with self.subTest(case=case):
                        command = [*prefix, "test", *flags, *home_flags, "//:home"]
                        (artifacts / (case + "-command.json")).write_text(json.dumps(command, indent=2) + "\n")
                        log_path = artifacts / (case + ".log")
                        with log_path.open("w") as log:
                            result = subprocess.run(command, cwd=consumer, env=environment, stdout=log,
                                                    stderr=subprocess.STDOUT, timeout=bazel_timeout)
                        transcript = log_path.read_text()
                        if succeeds:
                            self.assertEqual(result.returncode, 0, transcript)
                        else:
                            self.assertNotEqual(result.returncode, 0, transcript)
                            self.assertIn("HOME must reach Python as the per-test directory", transcript)
            finally:
                destination = os.environ.get("REGISTRY_CI_TEST_ARTIFACTS")
                if destination:
                    shutil.copytree(artifacts, Path(destination) / work.name)


if __name__ == "__main__":
    unittest.main()
