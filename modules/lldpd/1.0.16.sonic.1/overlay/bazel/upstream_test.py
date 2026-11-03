"""Run the unchanged upstream protocol/parser suites with declared libraries."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

root = Path(sys.argv[1]).resolve()
loader = root / "usr/lib/x86_64-linux-gnu/ld-linux-x86-64.so.2"
libraries = root / "usr/lib/x86_64-linux-gnu"
with tempfile.TemporaryDirectory(prefix="lldpd-check-") as temporary:
    for binary in sys.argv[2:]:
        command = [str(loader), "--inhibit-cache", "--library-path", str(libraries), str(Path(binary).resolve())]
        print("Upstream suite:", Path(binary).name, flush=True)
        subprocess.run(command, check=True, cwd=temporary, env={"HOME": temporary, "LC_ALL": "C", "CK_DEFAULT_TIMEOUT": "60"})
