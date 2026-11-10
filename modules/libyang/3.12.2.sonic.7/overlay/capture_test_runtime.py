"""Materialize only the runtime already validated by infra's instrument hook.

This is a build-time capture, not target execution. The test launcher later
executes the original target ELF with this exact loader/library closure.
"""

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import stat
import struct


def digest(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def target_elf(path, machine):
    with path.open("rb") as source:
        header = source.read(20)
    if len(header) != 20 or header[:6] != b"\x7fELF\x02\x01" or struct.unpack_from("<H", header, 18)[0] != machine:
        raise ValueError(f"Unexpected target ELF architecture: {path.name}")


def capture(args):
    command = args.command
    if len(command) != 5 or command[1] != "--inhibit-cache" or command[2] != "--library-path":
        raise ValueError("Expected the validator's exact loader/library-path/binary command")
    loader, root, binary = Path(command[0]), Path(command[3]), Path(command[4])
    if not stat.S_ISDIR(root.lstat().st_mode) or loader.parent != root:
        raise ValueError("Loader must be in the validator's regular runtime directory")
    if not re.fullmatch(r"[A-Za-z0-9_.+-]+", loader.name):
        raise ValueError("Unsafe loader basename")
    target_elf(binary, args.machine)
    records = []
    for source in sorted(root.rglob("*")):
        mode = source.lstat().st_mode
        if stat.S_ISDIR(mode):
            continue
        if not stat.S_ISREG(mode):
            raise ValueError("Validated runtime capture must contain only directories and regular files")
        target_elf(source, args.machine)
        records.append((source, source.relative_to(root), stat.S_IMODE(mode), digest(source)))
    if not any(source == loader for source, _, _, _ in records):
        raise ValueError("Validated loader missing")
    template = args.template.read_text()
    if template.count("@@LOADER@@") != 1 or re.search(r"@@(?!LOADER@@)[A-Z_]+@@", template):
        raise ValueError("Launcher template has unexpected unresolved substitutions")
    if args.runtime.resolve() == root.resolve() or root.resolve() in args.runtime.resolve().parents:
        raise ValueError("Output runtime must be separate from the validator's temporary runtime")
    args.runtime.mkdir(parents=True, exist_ok=True)
    if any(args.runtime.iterdir()):
        raise ValueError("Output runtime is not empty")
    for source, relative, mode, expected_digest in records:
        destination = args.runtime / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        destination.chmod(mode)
        if digest(destination) != expected_digest:
            raise ValueError("Copied runtime bytes changed")
    manifest = {
        "format": 1,
        "validation": "sonic-build-infra runtime_test.py instrument boundary; target execution occurs in tests",
        "validator_sha256": digest(args.validator),
        "target_machine": args.machine,
        "target_binary_sha256": digest(binary),
        "loader": loader.name,
        "files": [{"path": relative.as_posix(), "sha256": expected_digest, "mode": mode} for _, relative, mode, expected_digest in records],
    }
    args.manifest.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
    args.launcher.write_text(template.replace("@@LOADER@@", loader.name))
    args.launcher.chmod(0o755)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ("runtime", "manifest", "launcher", "template", "validator"):
        parser.add_argument("--" + option, type=Path, required=True)
    parser.add_argument("--machine", type=int, choices=(62, 183), required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.command and args.command[0] == "--":
        args.command = args.command[1:]
    capture(args)


if __name__ == "__main__":
    main()
