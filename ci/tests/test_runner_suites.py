"""The CI suite split preserves native coverage and requires the cross fixture."""

import contextlib
import importlib.util
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


SPEC = importlib.util.spec_from_file_location("runner_suites", Path(__file__).resolve().parents[1] / "run_runner_tests.py")
runner_suites = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner_suites)


def test_ids(suite):
    for test in suite:
        if isinstance(test, unittest.TestSuite):
            yield from test_ids(test)
        else:
            yield test.id()


class RunnerSuiteTests(unittest.TestCase):
    def test_native_and_cross_partition_full_discovery_without_duplicates(self):
        native = list(test_ids(runner_suites.discover("native")))
        cross = list(test_ids(runner_suites.discover("cross")))
        complete = list(test_ids(unittest.TestLoader().discover(str(runner_suites.TESTS))))
        self.assertTrue(native)
        self.assertTrue(cross)
        self.assertFalse(set(native) & set(cross))
        self.assertCountEqual(native + cross, complete)
        self.assertEqual(len(complete), len(set(complete)))
        self.assertTrue(all(name.startswith("test_arm_cross_runtime.") for name in cross))
        self.assertFalse(any(name.startswith("test_arm_cross_runtime.") for name in native))

    def test_new_native_files_join_coverage_without_editing_a_test_list(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            names = ("test_future_runner_native", "test_future_runner_cross")
            for name in names:
                (root / (name + ".py")).write_text(
                    "import unittest\nclass Fixture(unittest.TestCase):\n"
                    "    def test_present(self): pass\n")
                self.addCleanup(sys.modules.pop, name, None)
            with mock.patch.object(runner_suites, "TESTS", root), \
                    mock.patch.object(runner_suites, "CROSS_MODULE", names[1] + ".py"):
                self.assertEqual(list(test_ids(runner_suites.discover("native"))),
                                 [names[0] + ".Fixture.test_present"])
                self.assertEqual(list(test_ids(runner_suites.discover("cross"))),
                                 [names[1] + ".Fixture.test_present"])

    def test_cross_requires_both_absolute_executables_before_loading_tests(self):
        names = ("REGISTRY_CI_TEST_BAZEL", "REGISTRY_CI_TEST_ARM_EXECUTOR")
        with tempfile.TemporaryDirectory() as temporary:
            executable = Path(temporary) / "executable"
            executable.write_text("#!/bin/sh\nexit 99\n")
            executable.chmod(0o755)
            valid = dict.fromkeys(names, str(executable))
            for name in names:
                for invalid in ("", "relative-program", str(executable.parent), str(executable) + ".missing"):
                    with self.subTest(name=name, invalid=invalid), \
                            mock.patch.dict(os.environ, {**valid, name: invalid}), \
                            mock.patch.object(runner_suites, "discover") as discover, \
                            contextlib.redirect_stderr(io.StringIO()) as errors:
                        self.assertEqual(runner_suites.main(["--suite", "cross"]), 2)
                        discover.assert_not_called()
                        self.assertIn(name, errors.getvalue())
            executable.chmod(0o644)
            with mock.patch.dict(os.environ, valid), self.assertRaises(ValueError):
                runner_suites.cross_prerequisites()

    def test_cross_rejects_skips_and_failures_while_native_keeps_opt_in_skips(self):
        def passes():
            pass

        def skips():
            raise unittest.SkipTest("synthetic missing prerequisite")

        def fails():
            raise AssertionError("synthetic test failure")

        for kind, test, expected in (("cross", passes, 0), ("cross", skips, 1),
                                     ("cross", fails, 1), ("native", skips, 0),
                                     ("native", fails, 1)):
            with self.subTest(kind=kind, test=test.__name__), \
                    mock.patch.object(runner_suites, "cross_prerequisites") as prerequisites, \
                    mock.patch.object(runner_suites, "discover", return_value=unittest.TestSuite([
                        unittest.FunctionTestCase(test)])), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(runner_suites.main(["--suite", kind]), expected)
                self.assertEqual(prerequisites.call_count, int(kind == "cross"))

    def test_missing_cross_module_is_an_error(self):
        with tempfile.TemporaryDirectory() as temporary, \
                mock.patch.object(runner_suites, "TESTS", Path(temporary)):
            with self.assertRaisesRegex(ValueError, "empty: cross"):
                runner_suites.discover("cross")
