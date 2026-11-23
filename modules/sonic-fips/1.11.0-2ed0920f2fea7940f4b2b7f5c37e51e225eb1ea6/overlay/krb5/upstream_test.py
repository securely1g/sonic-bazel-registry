"""Run the unchanged upstream base64 assertions in Bazel's writable directory."""
import os
from pathlib import Path
import subprocess
import sys

binary = str(Path(sys.argv[1]).absolute())
os.chdir(os.environ["TEST_TMPDIR"])
raise SystemExit(subprocess.run([binary, *sys.argv[2:]]).returncode)
