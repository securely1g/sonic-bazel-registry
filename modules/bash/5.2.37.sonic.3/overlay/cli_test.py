"""Execute the built and installed Bash through their declared runtimes."""
import os
from pathlib import Path
import subprocess
import sys
import unittest

EXECUTABLES = [Path(value).absolute() for value in sys.argv[1:]]
del sys.argv[1:]

class CliTest(unittest.TestCase):
    def test_build_and_installed_shell_version(self):
        for executable in EXECUTABLES:
            result = subprocess.run([str(executable), "--version"], env={**os.environ, "LC_ALL": "C", "PATH": ""}, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertRegex(result.stdout, r"GNU bash, version 5\.2\.37\(1\)-release")

if __name__ == "__main__":
    unittest.main()
