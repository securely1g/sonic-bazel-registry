"""Check nested rules_go builds use native Bazel and return ARM64 outputs."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("rules_go_registry_ci", ROOT / "ci/registry_ci.py")
registry_ci = importlib.util.module_from_spec(spec)
spec.loader.exec_module(registry_ci)


class NestedGoBuildTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="nested go ")
        self.addCleanup(temporary.cleanup)
        self.work = Path(temporary.name)
        adapter = self.work / "cross-cc-repository"
        adapter.mkdir()
        (adapter / "BUILD.bazel").touch()
        host_bazel = self.work / "native bazel"
        host_bazel.write_text(
            f"#!{sys.executable}\n"
            "import json, sys\n"
            "with open('calls', 'a') as f: f.write(json.dumps(sys.argv[1:]) + '\\n')\n"
            "if 'cquery' in sys.argv: print('go output')\n"
            "if 'version' in sys.argv: sys.exit(17)\n"
        )
        host_bazel.chmod(0o755)
        executor = registry_ci.prepare_nested_go_tests(ROOT, self.work, str(host_bazel))
        self.nested = executor.with_name("bazel")
        self.assertEqual(self.nested.with_name("source_mirrors.cfg").read_bytes(),
                         (ROOT / "ci/source_mirrors.cfg").read_bytes())

    def test_nested_build_checks_each_target_executable(self):
        for machine, expected_success in ((183, True), (62, False)):
            with self.subTest(machine=machine):
                (self.work / "go output").write_bytes(b"\x7fELF\x02\x01" + bytes(12) + machine.to_bytes(2, "little"))
                call = subprocess.run([self.nested, "build", "//:go"], cwd=self.work, capture_output=True, text=True)
                self.assertEqual(call.returncode == 0, expected_success, call.stderr)
                commands = [json.loads(line) for line in (self.work / "calls").read_text().splitlines()][-2:]
                self.assertIn("build", commands[0])
                self.assertIn("cquery", commands[1])
                for args in commands:
                    self.assertIn("--platforms=@registry_ci_cross_cc//nested:arm64", args)
                    self.assertIn("--host_platform=@registry_ci_cross_cc//nested:amd64", args)
                    self.assertIn("--extra_toolchains=@registry_ci_cross_cc//:toolchain", args)
                    self.assertIn("//:go", args)

    def test_non_build_commands_keep_original_arguments_and_status(self):
        cmd = ["--output_user_root", "/path with spaces", "version"]
        self.assertEqual(subprocess.run([self.nested, *cmd], cwd=self.work).returncode, 17)
        self.assertEqual(json.loads((self.work / "calls").read_text()), cmd)
