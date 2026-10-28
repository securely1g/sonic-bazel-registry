"""Verify source-line lookup from the delivered runtime and matching symbol TARs.

Run after registry_ci.py run, using the GDB explicitly installed by native CI.
The contract is inherited from .sonic.5's libyang_package_test.sh.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import tempfile


def checksum(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(artifacts):
    artifacts = artifacts.resolve()
    manifest = artifacts / "outputs.json"
    outputs = json.loads(manifest.read_text())
    receipt = {"outputs_manifest_sha256": checksum(manifest), "archives": []}
    with tempfile.TemporaryDirectory(prefix="libyang-symbols-") as temporary:
        root = Path(temporary)
        for label, destination in (("@libyang//:libyang_pkg", root / "runtime"),
                                   ("@libyang//:libyang_pkg.debug_symbols", root / "symbols")):
            archives = outputs[label]
            if len(archives) != 1:
                raise SystemExit("Expected one delivered archive for " + label)
            record = archives[0]
            archive = (artifacts / record["path"]).resolve()
            if not archive.is_relative_to(artifacts / "outputs"):
                raise SystemExit("Archive must remain inside collected outputs")
            if archive.stat().st_size != record["size"] or checksum(archive) != record["sha256"]:
                raise SystemExit("Collected archive does not match outputs.json: " + record["path"])
            receipt["archives"].append(record)
            destination.mkdir()
            with tarfile.open(archive) as source:
                source.extractall(destination, filter="data")
        libraries = list((root / "runtime").glob("usr/lib/*/libyang.so.3.9.1"))
        if len(libraries) != 1:
            raise SystemExit("Expected one installed libyang runtime library")
        result = subprocess.run(
            ["gdb", "-nx", "-batch", "-iex", "set auto-load off",
             "-ex", "set debuginfod enabled off",
             "-ex", f"set debug-file-directory {root}/symbols/usr/lib/debug",
             "-ex", f"file {libraries[0]}", "-ex", "info line ly_ctx_new"],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            env=dict(os.environ, LC_ALL="C"), timeout=60,
        )
        (artifacts / "gdb-source-line.log").write_text(result.stdout)
        print(result.stdout, end="")
        if result.returncode or not re.search(r'Line [0-9]+ of .*context\.c', result.stdout):
            raise SystemExit("Delivered debug symbols do not resolve ly_ctx_new to context.c")
        receipt["runtime_sha256"] = checksum(libraries[0])
        receipt["line_lookup"] = result.stdout.strip()
    return receipt


def main():
    artifacts = Path(sys.argv[1]).resolve()
    receipt = check(artifacts)
    (artifacts / "libyang-installed-debug.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
