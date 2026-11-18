"""The fixed BIOS setup tool publishes its source version and raw-image CLI."""
from pathlib import Path
import subprocess
import sys

tool = str(Path(sys.argv[1]).absolute())
version = subprocess.check_output([tool, '--version'], text=True)
assert '2.12' in version, version
help_text = subprocess.check_output([tool, '--help'], text=True)
for option in ['--directory', '--device-map', '--skip-fs-probe']:
    assert option in help_text, option
