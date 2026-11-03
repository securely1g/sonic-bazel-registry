"""Run Scapy's declared upstream wheel backend without network or isolation."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

source = Path(sys.argv[1]).resolve().parent
output = Path(sys.argv[2]).resolve()
# Bazel's Python tool runfiles provide these pinned frontend/backend packages.
env = dict(os.environ, PYTHONPATH=os.pathsep.join(str(Path(p).resolve()) for p in sys.path if p),
           PYTHONDONTWRITEBYTECODE="1", PYTHONNOUSERSITE="1", PIP_NO_INDEX="1",
           PYTHONHASHSEED="0", SOURCE_DATE_EPOCH="1730795594", SCAPY_VERSION="2.6.1.dev0")
with tempfile.TemporaryDirectory(prefix="scapy-wheel-") as temporary:
    root = Path(temporary)
    private = root / "source"
    private.mkdir()
    shutil.copytree(source / "scapy", private / "scapy",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for name in ("setup.py", "pyproject.toml", "MANIFEST.in", "README.md", "LICENSE", "run_scapy"):
        shutil.copy2(source / name, private / name)
    (private / "doc").mkdir()
    shutil.copy2(source / "doc/scapy.1", private / "doc/scapy.1")
    subprocess.run([sys.executable, "-m", "build", "--wheel", "--no-isolation",
                    "--outdir", str(root / "dist"), str(private)], cwd=root, env=env, check=True)
    shutil.copyfile(root / "dist" / output.name, output)
