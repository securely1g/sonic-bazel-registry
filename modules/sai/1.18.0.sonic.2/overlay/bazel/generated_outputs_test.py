"""Require byte-identical outputs when moving the sairedis SAI generator."""
import hashlib
import json
from pathlib import Path
import sys

expected = json.loads(Path(sys.argv[1]).read_text())
actual = {Path(name).name: hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in sys.argv[2:]}
if actual != expected:
    raise SystemExit(f"Generated SAI output differs from the validated migration baseline: {actual}")
print(f"Verified {len(actual)} generated SAI files against the sairedis baseline")
