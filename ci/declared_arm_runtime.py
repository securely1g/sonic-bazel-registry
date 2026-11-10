#!/usr/bin/python3
"""Run selected test wrappers natively while their declared ELF runs through ARM binfmt."""

import json
import os
from pathlib import Path
import sys


def main() -> None:
    fixtures = json.loads(sys.argv[1])
    original = sys.argv[2:]
    command = original[original.index("--") + 1:]
    for wrapper, target in fixtures.items():
        if not command[0].endswith("/" + wrapper):
            continue
        runfiles = Path(os.environ["TEST_SRCDIR"]) / os.environ["TEST_WORKSPACE"] / ".."
        with (runfiles / target).open("rb") as binary:
            header = binary.read(20)
        if header[:6] != b"\x7fELF\x02\x01" or header[18:20] != b"\xb7\x00":
            raise SystemExit(f"Expected a declared 64-bit little-endian AArch64 ELF at {target}")
        print(f"Running original fixture through binfmt with AArch64 {target}", file=sys.stderr, flush=True)
        os.environ["QEMU_LD_PREFIX"] = "/opt/sonic-arm64-rootfs"
        os.execvp(command[0], command)
    os.execvp(original[0], original)


if __name__ == "__main__":
    main()
