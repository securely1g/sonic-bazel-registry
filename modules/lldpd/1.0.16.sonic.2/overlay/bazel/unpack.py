"""Extract pinned target dependency payloads using the declared BSD tar tool."""
import os
from pathlib import Path
import subprocess
import sys

tool, destination, *archives = sys.argv[1:]
root = Path(destination)
root.mkdir(parents=True, exist_ok=True)
for archive in sorted(archives):
    subprocess.run([tool, "-xf", archive, "-C", str(root), "--no-same-owner"], check=True)
for path in sorted(root.rglob("*")):
    if path.is_symlink() and os.readlink(path).startswith("/"):
        target = root / os.readlink(path).lstrip("/")
        path.unlink()
        path.symlink_to(os.path.relpath(target, path.parent))
