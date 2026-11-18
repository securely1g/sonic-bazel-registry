"""Run the unchanged Make plugin tests with their original relative fixture."""
from pathlib import Path
import subprocess
import sys
import tempfile

executable, configuration = [Path(value).absolute() for value in sys.argv[1:]]
with tempfile.TemporaryDirectory() as directory:
    (Path(directory) / "bash_plugins.conf").symlink_to(configuration)
    raise SystemExit(subprocess.run([str(executable)], cwd=directory).returncode)
