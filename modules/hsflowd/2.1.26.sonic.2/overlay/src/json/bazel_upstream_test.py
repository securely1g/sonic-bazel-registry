"""Run an unmodified cJSON test with its declared original fixtures."""

import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--json-patch-input", type=Path, required=True)
    parser.add_argument("--make-test", action="store_true")
    args = parser.parse_args()
    binary = args.binary.resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix="hsflowd-cjson-") as temporary:
        root = Path(temporary)
        tests = root / "tests"
        tests.mkdir()
        shutil.copytree(args.input.resolve(strict=True).parent, tests / "inputs")
        shutil.copytree(args.json_patch_input.resolve(strict=True).parent, tests / "json-patch-tests")
        # CTest runs from tests/, while the native Make test runs from src/json/.
        subprocess.run([str(binary)], cwd=root if args.make_test else tests,
                       check=True, timeout=90)


if __name__ == "__main__":
    main()
