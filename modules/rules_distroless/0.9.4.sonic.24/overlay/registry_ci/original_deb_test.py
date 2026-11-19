"""Both public archive targets must retain the exact downloaded DEB bytes."""
import hashlib
from pathlib import Path
import sys

for name in sys.argv[1:3]:
    data = Path(name).read_bytes()
    assert data.startswith(b"!<arch>\n"), name
    assert hashlib.sha256(data).hexdigest() == sys.argv[3], name
