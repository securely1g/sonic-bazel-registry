"""Run the original scanner driver on documented syntax; no sensor enumeration."""
from pathlib import Path
import re
import subprocess
import sys

# sensors.conf(5): chip selector and label statement lexical grammar.
text = 'chip "coretemp-*"\nlabel temp1 "CPU"\n'
result = subprocess.run([str(Path(sys.argv[1]).absolute())], input=text, text=True,
                        capture_output=True, check=True)
tokens = [re.sub(r"^\d+: ", "", line) for line in result.stdout.splitlines()]
assert tokens == ["CHIP", "NAME: coretemp-*", "EOL", "LABEL", "NAME: temp1", "NAME: CPU", "EOL", "EOF"], result.stdout
