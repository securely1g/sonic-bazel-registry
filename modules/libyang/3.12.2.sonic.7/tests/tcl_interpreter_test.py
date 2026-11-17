"""Exercise Tcltest's real per-file children through the declared launcher.

Pass an explicit Tcl interpreter with --tclsh; this test never selects a host
interpreter implicitly. The full module tests still use their declared runtime.
"""
import argparse
import ast
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest


parser = argparse.ArgumentParser(add_help=False)
parser.add_argument("--tclsh", required=True)
options, remaining = parser.parse_known_args()
TCLSH = Path(options.tclsh).absolute()
if not TCLSH.is_file() or not os.access(TCLSH, os.X_OK):
    raise SystemExit("--tclsh must name an executable interpreter")
sys.argv = [sys.argv[0], *remaining]
SOURCE = Path(__file__).resolve().parents[1] / "overlay/upstream_tests.py"
assignments = [node for node in ast.parse(SOURCE.read_text()).body
               if isinstance(node, ast.Assign)
               and any(isinstance(target, ast.Name)
                       and target.id == "TCL_TEST_BOOTSTRAP"
                       for target in node.targets)]
assert len(assignments) == 1
BOOTSTRAP = ast.literal_eval(assignments[0].value)


class TclInterpreterTest(unittest.TestCase):
    def run_suite(self, *, bootstrap, missing_interpreter=False):
        with tempfile.TemporaryDirectory(prefix="libyang Tcl traversal ") as tmp:
            root = Path(tmp)
            calls = root / "calls"
            wrapper = root / "declared tclsh"
            wrapper.write_text("#!/bin/sh\nset -eu\n"
                               "printf '%s\\037' \"$@\" >> \"$CALL_LOG\"\n"
                               "printf '\\n' >> \"$CALL_LOG\"\n"
                               "DECLARED_TCL_PID=$$\nexport DECLARED_TCL_PID\n"
                               f"exec {shlex.quote(str(TCLSH))} \"$@\"\n")
            wrapper.chmod(0o700)
            tests = root / "original tests"
            tests.mkdir()
            for index in range(2):
                (tests / f"case{index}.test").write_text('''package require tcltest
namespace import ::tcltest::*
test declared-child-1 {} -body {
    list [expr {$env(DECLARED_TCL_PID) == [pid]}] \
        [info exists env(LIBYANG_TCL_INTERPRETER)] \
        [info exists env(LIBYANG_TCL_TEST_SCRIPT)]
} -result {1 0 0}
cleanupTests
''')
            suite = tests / "all.tcl"
            suite.write_text('''package require tcltest
if {$argv0 ne $env(EXPECT_SUITE)} {error "original argv0 changed"}
if {$argc != 2 || $argv ne {-notfile {absent file}}} {error "original argv changed"}
proc tcltest::cleanupTestsHook {} {
    variable numTests
    set ::exitCode [expr {$numTests(Failed) > 0}]
}
tcltest::configure -testdir $env(TESTS_DIR)
tcltest::runAllTests
exit $exitCode
''')
            bootstrap_path = root / "bootstrap.tcl"
            bootstrap_path.write_text(BOOTSTRAP)
            env = {key: os.environ[key] for key in
                   ("RUNFILES_DIR", "RUNFILES_MANIFEST_FILE", "RUNFILES_MANIFEST_ONLY")
                   if key in os.environ}
            env.update(PATH="/usr/bin:/bin", HOME=str(root), LC_ALL="C",
                       CALL_LOG=str(calls), TESTS_DIR=str(tests), EXPECT_SUITE=str(suite),
                       LIBYANG_TCL_INTERPRETER=str(root / "missing" if missing_interpreter else wrapper),
                       LIBYANG_TCL_TEST_SCRIPT=str(suite))
            result = subprocess.run(
                [str(wrapper), str(bootstrap_path if bootstrap else suite), "-notfile", "absent file"],
                env=env, cwd=root, text=True, capture_output=True, timeout=15)
            invocations = [line.split("\x1f")[:-1] for line in calls.read_text().splitlines()]
            return result, invocations

    def test_every_child_uses_declared_interpreter_and_original_arguments(self):
        result, calls = self.run_suite(bootstrap=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertRegex(result.stdout, r"all\.tcl:\s+Total\s+2\s+Passed\s+2\s+Skipped\s+0\s+Failed\s+0")
        child_scripts = [Path(arg).name for call in calls for arg in call if arg.endswith(".test")]
        self.assertEqual(child_scripts, ["case0.test", "case1.test"])

    def test_original_raw_interpreter_path_is_detected(self):
        result, calls = self.run_suite(bootstrap=False)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertRegex(result.stdout, r"all\.tcl:\s+Total\s+2\s+Passed\s+0\s+Skipped\s+0\s+Failed\s+2")
        self.assertEqual(len(calls), 1, "raw children bypass the declared wrapper")

    def test_missing_declared_interpreter_fails_before_original_suite(self):
        result, calls = self.run_suite(bootstrap=True, missing_interpreter=True)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("declared Tcl interpreter is not executable", result.stderr)
        self.assertNotIn("all.tcl:", result.stdout)
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
