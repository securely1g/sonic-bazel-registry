#!/usr/bin/env python3
"""Run disjoint native-runner and ARM-cross test suites without silent cross skips."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys
import unittest


TESTS = Path(__file__).resolve().parent / "tests"
CROSS_MODULE = "test_arm_cross_runtime.py"


def discover(suite: str) -> unittest.TestSuite:
    """Partition by file before loading tests, including any future test files."""
    if suite not in {"native", "cross"}:
        raise ValueError(f"Unknown runner test suite: {suite}")
    selected = unittest.TestSuite()
    loader = unittest.TestLoader()
    for path in sorted(TESTS.glob("test_*.py")):
        if (path.name == CROSS_MODULE) == (suite == "cross"):
            selected.addTests(loader.discover(str(TESTS), pattern=path.name))
    if not selected.countTestCases():
        raise ValueError(f"Runner test suite is empty: {suite}")
    return selected


def cross_prerequisites() -> None:
    for name in ("REGISTRY_CI_TEST_BAZEL", "REGISTRY_CI_TEST_ARM_EXECUTOR"):
        value = os.environ.get(name, "")
        path = Path(value)
        if not value or not path.is_absolute() or not path.is_file() or not os.access(path, os.X_OK):
            raise ValueError(f"{name} must name an existing absolute executable for the cross fixture")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", choices=("native", "cross"), required=True)
    options = parser.parse_args(argv)
    try:
        if options.suite == "cross":
            cross_prerequisites()
        tests = discover(options.suite)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2
    result = unittest.TextTestRunner(verbosity=2).run(tests)
    if options.suite == "cross" and result.skipped:
        print("The required ARM cross fixture skipped tests", file=sys.stderr)
        return 1
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
