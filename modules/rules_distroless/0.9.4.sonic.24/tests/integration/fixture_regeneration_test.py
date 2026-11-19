"""The fixture selector must reproduce the reviewed lock without modifying it."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

helper, fixture = map(Path, sys.argv[1:])
reviewed = fixture.read_bytes()
with tempfile.TemporaryDirectory(dir=os.environ.get("TEST_TMPDIR")) as temporary:
    regenerated = Path(temporary) / "apt.lock.json"
    subprocess.run([sys.executable, str(helper), "--input", str(fixture),
                    "--output", str(regenerated)], check=True)
    if regenerated.read_bytes() != reviewed or fixture.read_bytes() != reviewed:
        raise SystemExit("Fixture regeneration differs from the reviewed lock")
print("PASS: fixture regeneration preserves the reviewed lock")
