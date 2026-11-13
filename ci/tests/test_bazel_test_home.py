"""Check that Bazel preserves caller HOME and uses TEST_TMPDIR for writes."""

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
expected_home = json.loads(os.environ["REGISTRY_CI_EXPECTED_HOME"])
assert home == expected_home, "HOME must retain the invoking environment's value"
assert Path.home() == Path(expected_home)
assert temporary != home
print(json.dumps({"home_preserved": True, "writes_use_test_tmpdir": True}), flush=True)
assert os.environ["SONIC_TEST_RUNTIME_ID"] == "a" * 64
assert os.environ["REGISTRY_CI_HOME_MARKER"] == "preserved"
config = Path(temporary) / ".config"
config.mkdir(mode=0o700)
startup = config / "startup.py"
startup.write_text("test configuration")
assert startup.read_text() == "test configuration"
'''


@unittest.skipUnless(os.environ.get("REGISTRY_CI_TEST_BAZEL"),
                     "set REGISTRY_CI_TEST_BAZEL to run the real Bazel test HOME fixture")
class BazelTestHomeIntegrationTest(unittest.TestCase):
    def test_actual_home_is_preserved_and_writes_use_test_tmpdir(self):
        if not os.environ.get("HOME"):
            self.skipTest("This real integration requires a nonempty actual caller HOME")
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
                     "--test_env=REGISTRY_CI_HOME_MARKER=preserved",
                     "--test_env=REGISTRY_CI_EXPECTED_HOME=" + json.dumps(os.environ["HOME"]),
                     "--test_env=HOME"]
            environment = os.environ.copy()
            try:
                command = [*prefix, "test", *flags, "//:home"]
                (artifacts / "preserved-command.json").write_text(json.dumps(command, indent=2) + "\n")
                log_path = artifacts / "preserved.log"
                with log_path.open("w") as log:
                    result = subprocess.run(command, cwd=consumer, env=environment, stdout=log,
                                            stderr=subprocess.STDOUT, timeout=180)
                self.assertEqual(result.returncode, 0, log_path.read_text())
                self.assertEqual(os.environ.get("HOME"), environment["HOME"])
            finally:
                destination = os.environ.get("REGISTRY_CI_TEST_ARTIFACTS")
                if destination:
                    shutil.copytree(artifacts, Path(destination) / work.name)


if __name__ == "__main__":
    unittest.main()
