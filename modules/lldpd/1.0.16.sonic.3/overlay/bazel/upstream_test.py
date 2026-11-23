"""Run unchanged upstream suites in their declared target runtime."""
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
from bazel.package_test import extract

architecture, archive, *binaries = sys.argv[1:]
expected = {"amd64": {"x86_64", "amd64"}, "arm64": {"aarch64", "arm64"}}[architecture]
if platform.machine() not in expected:
    raise RuntimeError("Upstream execution requires a native " + architecture + " worker")
triplet, loader_name = {"amd64": ("x86_64-linux-gnu", "ld-linux-x86-64.so.2"), "arm64": ("aarch64-linux-gnu", "ld-linux-aarch64.so.1")}[architecture]
with tempfile.TemporaryDirectory(dir=os.environ.get("TEST_TMPDIR")) as temporary:
    root = Path(temporary)
    extract(archive, root)
    loader = root / "usr/lib" / triplet / loader_name
    libraries = root / "usr/lib" / triplet
    for binary in binaries:
        command = [str(loader), "--inhibit-cache", "--library-path", str(libraries), str(Path(binary).absolute())]
        print("Upstream suite:", Path(binary).name, flush=True)
        subprocess.run(command, check=True, cwd=temporary, env={"HOME": temporary, "LC_ALL": "C", "CK_DEFAULT_TIMEOUT": "60"})
