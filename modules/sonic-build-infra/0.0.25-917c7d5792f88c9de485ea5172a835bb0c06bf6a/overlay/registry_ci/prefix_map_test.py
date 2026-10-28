"""Check GCC's file-prefix mapping in a registered-module consumer."""

from pathlib import Path
import re
import subprocess
import sys
import tempfile


source, objcopy = sys.argv[1:3]
obj = next(Path(name) for name in sys.argv[3:] if name.endswith(".o"))
dwarf = next(Path(name) for name in sys.argv[3:] if name.endswith(".dwarf")).read_text()
expected = "./" + source

# GCC replaces the compilation working directory with '.', preserving the
# declared source's execpath, including its external repository directory.
for attribute, value in [("comp_dir", "."), ("name", expected)]:
    pattern = (r"\bDW_AT_" + attribute + r"[ \t]*:[ \t]*(?:\([^\n)]*\):[ \t]*)?"
               + re.escape(value) + r"[ \t]*$")
    assert re.search(pattern, dwarf, re.MULTILINE), dwarf

# Inspect the C string itself; the correct path appearing only in debug
# information must not mask an unmapped __FILE__ value.
with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    rodata = root / "rodata"
    subprocess.run(
        [objcopy, "--dump-section=.rodata=" + str(rodata), str(obj), str(root / "copy.o")],
        check=True,
    )
    assert expected.encode() in rodata.read_bytes().split(b"\0"), rodata.read_bytes()
