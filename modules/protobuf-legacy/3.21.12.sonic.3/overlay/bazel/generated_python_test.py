"""Verify declared Python/stub outputs from the matching generator."""
import ast
from pathlib import Path
import sys
from python.runfiles import runfiles

resolver = runfiles.Create()
assert resolver is not None
for logical in sys.argv[1:]:
    path = Path(resolver.Rlocation(logical))
    text = path.read_text()
    ast.parse(text, filename=str(path))
    assert "Probe" in text
assert "class Probe" in Path(resolver.Rlocation(sys.argv[2])).read_text()
