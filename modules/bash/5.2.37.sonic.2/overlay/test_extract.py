"""Read the exact deployment ELF rather than a private packager target."""
from pathlib import Path
import sys
import tarfile

with tarfile.open(sys.argv[1]) as archive:
    member = next(member for member in archive if member.name.removeprefix("./") == "usr/bin/bash")
    output = Path(sys.argv[2])
    output.write_bytes(archive.extractfile(member).read())
    output.chmod(member.mode)
