"""Generate egg metadata using upstream setup.py and declared setuptools."""
from pathlib import Path
import os
import runpy
import shutil
import sys
import tempfile

source, output = map(lambda value: Path(value).resolve(), sys.argv[1:])
with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    for name in ["setup.py", "README.rst", "MANIFEST.in", "libyang", "cffi"]:
        original = source / name
        if original.is_dir():
            shutil.copytree(original, root / name)
        elif original.is_file():
            shutil.copyfile(original, root / name)
    os.chdir(root)
    os.environ["LIBYANG_PYTHON_FORCE_VERSION"] = "3.1.0"
    sys.argv = ["setup.py", "egg_info"]
    runpy.run_path(str(root / "setup.py"), run_name="__main__")
    shutil.copytree(root / "libyang.egg-info", output / "usr/lib/python3/dist-packages/libyang-3.1.0.egg-info")
