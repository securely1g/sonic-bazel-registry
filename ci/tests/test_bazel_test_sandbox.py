"""Exercise hard-linked runfiles while retaining the build action sandbox."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


SPEC = importlib.util.spec_from_file_location(
    "registry_ci_sandbox_integration", Path(__file__).resolve().parents[1] / "registry_ci.py"
)
assert SPEC is not None and SPEC.loader is not None
registry_ci = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(registry_ci)

PROBE = '''#!/bin/bash
exec /usr/bin/python3 -I -S - <<'PYTHON'
import os
from pathlib import Path

source = (Path(os.environ["TEST_SRCDIR"]) / os.environ["TEST_WORKSPACE"] / "payload.txt").resolve()
target = Path(os.environ["TEST_TMPDIR"]) / "hardlinked-payload"
target.hardlink_to(source)
assert target.samefile(source)
assert target.read_bytes() == source.read_bytes()
print("HARDLINK_SAME_INODE_PASSED")
PYTHON
'''

LOCAL_PROBE = '''#!/bin/bash
exec /usr/bin/python3 -I -S - <<'PYTHON'
import os
from pathlib import Path

source = Path(os.environ["TEST_SRCDIR"]) / os.environ["TEST_WORKSPACE"] / "payload.txt"
assert source.read_text() == "production"
print("LOCAL_DECLARED_INPUT_PASSED")
PYTHON
'''


def execution_records(path: Path) -> list[dict]:
    """Bazel's JSON execution log contains consecutive, pretty-printed objects."""
    remaining = path.read_text().lstrip()
    decoder = json.JSONDecoder()
    records = []
    while remaining:
        record, end = decoder.raw_decode(remaining)
        records.append(record)
        remaining = remaining[end:].lstrip()
    return records


@unittest.skipUnless(os.environ.get("REGISTRY_CI_TEST_BAZEL"),
                     "set REGISTRY_CI_TEST_BAZEL to run the real Bazel hard-link fixture")
class BazelTestSandboxIntegrationTest(unittest.TestCase):
    def test_hardlinked_runfile_and_local_test_preserve_build_action_strategy(self):
        with tempfile.TemporaryDirectory(prefix="registry-bazel-hardlink-") as temporary:
            work = Path(temporary)
            consumer, artifacts = work / "consumer", work / "artifacts"
            consumer.mkdir()
            artifacts.mkdir()
            (consumer / "MODULE.bazel").write_text('module(name = "hardlink_fixture")\n')
            (consumer / "fixture.bzl").write_text(
                'def _payload(ctx):\n'
                '    output = ctx.actions.declare_file(ctx.label.name + ".txt")\n'
                '    ctx.actions.run_shell(outputs = [output], mnemonic = "FixtureBuild",\n'
                '        command = "printf %s " + ctx.attr.content + " > " + output.path)\n'
                '    return [DefaultInfo(files = depset([output]))]\n'
                'payload = rule(implementation = _payload, attrs = {"content": attr.string()})\n'
                'def _test(ctx):\n'
                '    script = ctx.actions.declare_file(ctx.label.name + ".sh")\n'
                f'    text = {json.dumps(PROBE)} if ctx.attr.hardlink else {json.dumps(LOCAL_PROBE)}\n'
                '    ctx.actions.write(script, text, is_executable = True)\n'
                '    return [DefaultInfo(executable = script,\n'
                '        runfiles = ctx.runfiles(files = ctx.files.data))]\n'
                'hardlink_test = rule(implementation = _test, test = True,\n'
                '    attrs = {"data": attr.label_list(allow_files = True),\n'
                '        "hardlink": attr.bool(default = True)})\n')
            # This probe must execute each action to verify its strategy, including
            # XML generation. A worker's shared cache cannot provide that proof.
            prefix = [os.environ["REGISTRY_CI_TEST_BAZEL"], "--batch", "--ignore_all_rc_files",
                      "--output_user_root=" + str(work / "bazel"), "test",
                      "--remote_cache=", "--disk_cache=",
                      "--incompatible_autoload_externally=", "--lockfile_mode=off",
                      "--host_platform=//:fixture_platform", "--platforms=//:fixture_platform",
                      "--test_env=HOME=", "--nocache_test_results", "--test_output=all"]

            def execute(case: str, build_strategy: str, test_strategy: str):
                # Change the producer action so the preceding case's output cannot
                # masquerade as proof of the requested build strategy.
                (consumer / "BUILD.bazel").write_text(
                    'load(":fixture.bzl", "payload", "hardlink_test")\n'
                    'platform(name = "fixture_platform")\n'
                    f'payload(name = "payload", content = "{case}")\n'
                    'hardlink_test(name = "hardlink", data = [":payload"])\n'
                    'hardlink_test(name = "local_read", data = [":payload"],\n'
                    '    hardlink = False, tags = ["exclusive", "local"])\n')
                execution_log = artifacts / (case + "-execution.json")
                command = [*prefix, "--spawn_strategy=" + build_strategy,
                           "--strategy=TestRunner=" + test_strategy,
                           "--execution_log_json_file=" + str(execution_log), "//:hardlink"]
                if case == "production":
                    command.append("//:local_read")
                (artifacts / (case + "-command.json")).write_text(json.dumps(command, indent=2) + "\n")
                log_path = artifacts / (case + ".log")
                with log_path.open("w") as log:
                    result = subprocess.run(command, cwd=consumer, stdout=log,
                                            stderr=subprocess.STDOUT, timeout=180)
                return result.returncode, log_path.read_text(), execution_log

            try:
                code, transcript, _ = execute("linux", "linux-sandbox", "linux-sandbox")
                self.assertNotEqual(code, 0, transcript)
                if "[Errno 18]" in transcript:
                    build_strategy = "linux-sandbox"
                else:
                    # Some containers disallow Linux namespaces. Keep exercising
                    # the production hard-link behavior there, without treating
                    # an unrelated fixture failure as missing sandbox support.
                    self.assertIn("'linux-sandbox' was requested", transcript)
                    self.assertIn("no strategy with that identifier was registered", transcript)
                    build_strategy = "processwrapper-sandbox"
                code, transcript, execution_log = execute(
                    "production", build_strategy, registry_ci.TEST_SANDBOX_STRATEGY)
                self.assertEqual(code, 0, transcript)
                self.assertIn("HARDLINK_SAME_INODE_PASSED", transcript)
                self.assertIn("LOCAL_DECLARED_INPUT_PASSED", transcript)
                records = execution_records(execution_log)
                builds = [record for record in records if record["mnemonic"] == "FixtureBuild"]
                tests = [record for record in records if record["mnemonic"] == "TestRunner"]
                ordinary_tests = [record for record in tests
                                  if record["targetLabel"].endswith("//:hardlink")]
                local_tests = [record for record in tests
                               if record["targetLabel"].endswith("//:local_read")]
                self.assertTrue(builds, records)
                self.assertTrue(ordinary_tests, records)
                self.assertTrue(local_tests, records)
                self.assertTrue(all(record["runner"] == build_strategy and not record["cacheHit"]
                                    for record in builds), builds)
                self.assertTrue(all(record["runner"] == "processwrapper-sandbox"
                                    and record["exitCode"] == 0 for record in ordinary_tests), ordinary_tests)
                self.assertTrue(all(record["runner"] == "local" and record["exitCode"] == 0
                                    for record in local_tests), local_tests)
                (artifacts / "result.json").write_text(json.dumps({
                    "build_strategy": build_strategy,
                    "requested_test_strategies": registry_ci.TEST_SANDBOX_STRATEGY,
                    "ordinary_test_strategy": "processwrapper-sandbox",
                    "local_test_strategy": "local",
                    "hardlink_same_inode": True,
                }, indent=2) + "\n")
            finally:
                destination = os.environ.get("REGISTRY_CI_TEST_ARTIFACTS")
                if destination:
                    shutil.copytree(artifacts, Path(destination) / work.name)


if __name__ == "__main__":
    unittest.main()
