"""Validate delivered libnl3 symbols with the registry CI container's GDB.

This post-build check complements the hermetic archive checks. It restores the
published package test's GDB source/line assertions without adding host tools to
the Bazel source build or changing any published recipe.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tarfile
import tempfile


STEMS = ("libnl-3", "libnl-genl-3", "libnl-route-3", "libnl-nf-3", "libnl-cli-3")


def checksum(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(artifacts):
    artifacts = artifacts.resolve()
    manifest = artifacts / "outputs.json"
    outputs = json.loads(manifest.read_text())
    records = {}
    for group in outputs.values():
        for record in group:
            previous = records.setdefault(record["path"], record)
            assert previous == record, ("conflicting output records", record["path"])

    def archive(stem, suffix):
        selected = [r for r in records.values()
                    if Path(r["path"]).name.startswith(stem + "_pkg_")
                    and r["path"].endswith(suffix)]
        assert len(selected) == 1, (stem, suffix, selected)
        record = selected[0]
        path = (artifacts / record["path"]).resolve()
        assert path.is_relative_to(artifacts / "outputs"), path
        assert path.stat().st_size == record["size"], path
        assert checksum(path) == record["sha256"], path
        return path, record

    result = {"outputs_manifest_sha256": checksum(manifest), "archives": [], "elfs": []}
    environment = dict(os.environ, LC_ALL="C")
    with tempfile.TemporaryDirectory(prefix="libnl3-debug-") as directory:
        for stem in STEMS:
            runtime = Path(directory) / stem / "runtime"
            symbols = Path(directory) / stem / "symbols"
            for root, suffix in ((runtime, "_rttar.tar"), (symbols, ".debug_symbols.tar")):
                path, record = archive(stem, suffix)
                root.mkdir(parents=True)
                with tarfile.open(path) as source:
                    source.extractall(root, filter="data")
                result["archives"].append(record)
            elfs = [p for p in runtime.rglob("*") if p.is_file() and not p.is_symlink()
                    and p.read_bytes()[:4] == b"\x7fELF"]
            assert len(elfs) == (11 if stem == "libnl-cli-3" else 1), (stem, elfs)
            for binary in sorted(elfs):
                command = ["gdb", "--batch", "--nx", "--quiet",
                           "-ex", "set debuginfod enabled off",
                           "-ex", "set auto-load off",
                           "-ex", "set debug-file-directory " + str(symbols / "usr/lib/debug"),
                           "-ex", "file " + str(binary)]
                sources = subprocess.check_output(command + ["-ex", "info sources"],
                                                  text=True, stderr=subprocess.STDOUT,
                                                  env=environment, timeout=60)
                paths = re.findall(r"[^,\s]+/lib/[^,\s]+\.c(?=[,\s]|$)", sources)
                assert paths, (str(binary), sources)
                lines = subprocess.check_output(command + ["-ex", "info line " + paths[0] + ":1"],
                                                text=True, stderr=subprocess.STDOUT,
                                                env=environment, timeout=60)
                assert re.search(r"Line \d+ of .* (?:starts at address|is at address)", lines), lines
                result["elfs"].append({"runtime": binary.relative_to(runtime).as_posix(),
                                       "runtime_sha256": checksum(binary),
                                       "source": paths[0], "line_lookup": lines.strip()})
    assert len(result["elfs"]) == 15
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", required=True, type=Path)
    args = parser.parse_args()
    receipt = check(args.artifacts)
    (args.artifacts / "libnl3-installed-debug.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print("GDB found source and line information for all 5 libraries and 10 CLI plugins")
