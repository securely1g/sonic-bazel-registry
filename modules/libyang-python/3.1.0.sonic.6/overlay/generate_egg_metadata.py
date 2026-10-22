"""Run upstream setup.py egg_info with the declared execution dependencies."""

import argparse
import os
from pathlib import Path
import runpy
import shutil
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--setup", required=True, type=lambda value: Path(value).resolve())
    parser.add_argument("--output", required=True, type=lambda value: Path(value).resolve())
    parser.add_argument("--expected", required=True, nargs="+")
    args = parser.parse_args()
    source = args.setup.parent

    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        for name in ("setup.py", "setup.cfg", "README.rst", "MANIFEST.in", "LICENSE",
                     "libyang", "cffi"):
            original = source / name
            if original.is_dir():
                shutil.copytree(original, root / name)
            else:
                shutil.copyfile(original, root / name)
        os.chdir(root)
        # The tagged source need not contain a Git checkout. Use upstream's
        # supported version input, and keep setup-time dependency fetches offline.
        os.environ.update(
            LIBYANG_PYTHON_FORCE_VERSION="3.1.0",
            LIBYANG_INSTALL="system",
            PIP_NO_INDEX="1",
            PIP_DISABLE_PIP_VERSION_CHECK="1",
        )
        sys.argv = ["setup.py", "egg_info"]
        runpy.run_path(str(root / "setup.py"), run_name="__main__")
        metadata = root / "libyang.egg-info"
        actual = {path.name for path in metadata.iterdir() if path.is_file()}
        expected = set(args.expected)
        if actual != expected or any(path.is_dir() for path in metadata.iterdir()):
            raise RuntimeError(
                f"Upstream egg metadata changed: expected {sorted(expected)}, got {sorted(actual)}"
            )
        args.output.mkdir(parents=True, exist_ok=True)
        for name in args.expected:
            shutil.copyfile(metadata / name, args.output / name)


if __name__ == "__main__":
    main()
