"""Run unchanged upstream sshkey assertions with their original fixture directory."""
import os
from pathlib import Path
import subprocess
import sys

if os.environ.get("SKIP_UNIT"):
    print("OpenSSH unit tests disabled by original SKIP_UNIT setting")
    raise SystemExit(0)

binary = str(Path(sys.argv[1]).absolute())
arguments = ["-d", str(Path(sys.argv[2]).absolute().parent)]
os.chdir(os.environ["TEST_TMPDIR"])
raise SystemExit(subprocess.run([binary, *arguments]).returncode)
