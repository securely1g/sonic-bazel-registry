"""Debian rules' first-line interpreter substitution, preserving all other bytes."""
from pathlib import Path
import re
import sys
source, output = map(Path, sys.argv[1:])
first, newline, body = source.read_bytes().partition(b'\n')
replacement, changed = re.subn(rb'^#!.*python[^ ]*(.*)$', rb'#! /usr/bin/python3.13\1', first)
if changed != 1:
    raise SystemExit('original Python shebang expected: ' + str(source))
output.write_bytes(replacement + newline + body)
