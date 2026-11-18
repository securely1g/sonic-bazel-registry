"""Run the original Debian shellcheck source selection and exclusions."""
from pathlib import Path
import re
import subprocess
import sys
scripts = [path for path in sys.argv[2:] if re.search(r"^#! */bin/(ba)?sh", Path(path).read_text(), flags=re.MULTILINE)]
if not scripts:
    raise ValueError("Original kdump-tools shell test source set is empty")
raise SystemExit(subprocess.run([sys.argv[1], "-e", "SC1090,SC1091,SC3043"] + scripts).returncode)
