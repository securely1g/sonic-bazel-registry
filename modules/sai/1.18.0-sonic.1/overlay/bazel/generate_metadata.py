"""Run the SAI metadata generators with declared inputs and execution tools."""

from __future__ import annotations

import argparse
import json
import platform
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


def main() -> None:
    parser = argparse.ArgumentParser()
    for name in ("manifest", "execution-image", "tools-recipe", "doxygen", "perl", "source-out", "header-out", "test-out", "swig-out"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--perl-option", action="append", default=[])
    args = parser.parse_args()
    inputs = json.loads(Path(args.manifest).read_text())
    sources = [(Path(entry["source"]).resolve(), entry["destination"]) for entry in inputs]
    # The launcher/workflow starts this exact digest; the marker rejects an
    # accidental host build. Including both pins in action arguments makes
    # container upgrades invalidate local and remote metadata cache entries.
    if not re.fullmatch(r"[^\s]+@sha256:[0-9a-f]{64}", args.execution_image):
        raise RuntimeError("SAI metadata requires a digest-pinned execution image")
    marker = Path("/etc/sonic-build-tools.json")
    if not marker.is_file():
        raise RuntimeError("Run SAI metadata generation inside " + args.execution_image)
    toolchain = json.loads(marker.read_text())
    architecture = {"x86_64": "amd64", "aarch64": "arm64"}.get(platform.machine())
    if (toolchain.get("schema_version") != 1
            or toolchain.get("recipe_sha256") != args.tools_recipe
            or architecture is None
            or toolchain.get("architecture") != architecture):
        raise RuntimeError("SAI build-tools container recipe or architecture does not match " + args.execution_image)
    doxygen = [args.doxygen]
    perl = str(Path(args.perl).resolve())
    outputs = {
        "saimetadata.c": Path(args.source_out).resolve(),
        "saimetadata.h": Path(args.header_out).resolve(),
        "saimetadatatest.c": Path(args.test_out).resolve(),
        "saiswig.i": Path(args.swig_out).resolve(),
    }
    with tempfile.TemporaryDirectory(prefix="sai-metadata-") as temporary:
        root = Path(temporary) / "SAI"
        for directory in ("inc", "experimental", "custom", "meta"):
            (root / directory).mkdir(parents=True, exist_ok=True)
        for source, destination in sources:
            target = root / destination
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        meta = root / "meta"
        home = Path(temporary) / "home"
        home.mkdir()
        environment = {
            "HOME": str(home),
            "LANG": "C",
            "LC_ALL": "C",
            "PATH": "/usr/bin:/bin",
            "TMPDIR": temporary,
        }
        version_result = subprocess.run(doxygen + ["-v"], check=True, capture_output=True, text=True, env=environment)
        match = re.search(r"(\d+)\.(\d+)\.(\d+)", version_result.stdout)
        if not match:
            raise RuntimeError("could not parse declared doxygen version: " + version_result.stdout)
        config = "Doxyfile" if tuple(map(int, match.groups())) >= (1, 8, 16) else "Doxyfile.compat"
        result = subprocess.run(doxygen + [config], cwd=meta, capture_output=True, text=True, env=environment)
        doxygen_output = result.stdout + result.stderr
        if result.returncode or "warning" in doxygen_output.lower():
            raise RuntimeError("doxygen failed or emitted a warning:\n" + doxygen_output)
        subprocess.run([perl, *args.perl_option, "-I.", "parse.pl"], cwd=meta, check=True, env=environment)
        for filename, output in outputs.items():
            output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(meta / filename, output)


if __name__ == "__main__":
    main()
