"""Verify actual extracted payload bytes and permissions, independent of SDK helpers."""
from pathlib import Path
import stat
import sys

for path, contents, mode in [
    (sys.argv[1], b"independent tar payload\n", 0o755),
    (sys.argv[2], b"#!/bin/sh\nexit 0\n", 0o755),
]:
    file = Path(path)
    assert file.read_bytes() == contents, path
    assert stat.S_IMODE(file.stat().st_mode) & 0o555 == mode & 0o555, path
