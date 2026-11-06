#!/usr/bin/python3
"""Run selected test wrappers natively while their declared ELF runs through ARM binfmt."""

import json
import os
from pathlib import Path
import sys


ARM_ROOTFS = Path("/opt/sonic-arm64-rootfs")


def main() -> None:
    fixtures = json.loads(sys.argv[1])
    original = sys.argv[2:]
    command = original[original.index("--") + 1:]
    for wrapper, target in fixtures.items():
        if not command[0].endswith("/" + wrapper):
            continue
        if target == {"arm_shell": "bash"}:
            # Package inspections require target binutils and GDB. Start their
            # original script with ARM Bash and resolve its tools in that rootfs.
            tools = ARM_ROOTFS / "usr/bin"
            payload = tools / "bash"
            os.environ["PATH"] = str(tools) + os.pathsep + os.environ.get("PATH", os.defpath)
            command = [str(payload), *command]
            target = str(payload)
        elif isinstance(target, str):
            runfiles = Path(os.environ["TEST_SRCDIR"]) / os.environ["TEST_WORKSPACE"] / ".."
            payload = runfiles / target
        else:
            raise SystemExit(f"Unknown ARM fixture configuration for {wrapper}")
        with payload.open("rb") as binary:
            header = binary.read(20)
        if header[:6] != b"\x7fELF\x02\x01" or header[18:20] != b"\xb7\x00":
            raise SystemExit(f"Expected a 64-bit little-endian AArch64 ELF at {target}")
        print(f"Running original fixture through binfmt with AArch64 {target}", file=sys.stderr, flush=True)
        os.environ["QEMU_LD_PREFIX"] = str(ARM_ROOTFS)
        os.execvp(command[0], command)
    os.execvp(original[0], original)


if __name__ == "__main__":
    main()
