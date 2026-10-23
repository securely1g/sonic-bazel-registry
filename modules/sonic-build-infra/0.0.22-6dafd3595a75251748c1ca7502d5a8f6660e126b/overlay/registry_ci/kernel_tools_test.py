"""Reuse the source kernel tools regression appropriate to native execution."""
from pathlib import Path
import subprocess
import sys

if __name__ == "__main__":
    subprocess.run([str(Path(sys.argv[1]).absolute()), *sys.argv[2:]], check=True)
