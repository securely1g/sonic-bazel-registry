"""Run the unmodified upstream libyang-Python unittest suite."""

import os
import shutil
import sys
import unittest
from pathlib import Path


def main():
    staged = Path(os.environ["TEST_TMPDIR"]) / "upstream"
    for argument in sys.argv[1:]:
        source = Path(argument)
        try:
            tests_index = source.parts.index("tests")
        except ValueError as error:
            raise AssertionError(f"Input is outside the upstream tests tree: {source}") from error
        relative = Path(*source.parts[tests_index:])
        destination = staged / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)

    tests = staged / "tests"
    suite = unittest.defaultTestLoader.discover(str(tests), pattern="test_*.py")
    count = suite.countTestCases()
    if count == 0:
        raise AssertionError(f"No upstream tests discovered under {tests}")
    print(f"Discovered {count} upstream tests")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
