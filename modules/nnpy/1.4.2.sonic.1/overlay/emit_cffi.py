"""Run nnpy's unchanged generator and setuptools metadata on declared inputs."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tempfile


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("setup", "headers", "library", "bsdtar", "output"):
        parser.add_argument("--" + name, required=True, type=lambda p: Path(p).resolve())
    args = parser.parse_args()
    source = args.setup.parent
    names = ["setup.py", "generate.py", "LICENSE", "MANIFEST.in", "README.rst"]
    names += ["nnpy/" + name for name in ("__init__.py", "errors.py", "socket.py", "tests.py")]
    with tempfile.TemporaryDirectory(prefix="nnpy-generate-") as temporary:
        root = Path(temporary)
        private = root / "source"
        for name in names:
            target = private / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / name, target)
        native = root / "native"
        native.mkdir()
        # The standard tar tool extracts the two declared execution-platform
        # payloads. Neither the generator nor setuptools discovers host headers.
        for archive in (args.headers, args.library):
            subprocess.run([args.bsdtar, "-xf", archive, "-C", native], check=True)
        headers = native / "usr/include/nanomsg"
        library = native / "usr/lib/x86_64-linux-gnu/libnanomsg.so.5"
        if not library.is_file() or not (headers / "nn.h").is_file():
            raise RuntimeError("The declared AMD64 nanomsg ABI inputs are incomplete")
        (private / "site.cfg").write_text(
            "[DEFAULT]\ninclude_dirs=" + str(headers) + "\n"
            "library_dirs=" + str(library.parent) + "\n"
            "host_library=" + str(library) + "\n"
        )
        os.chdir(private)
        os.environ.pop("CPATH", None)
        os.environ.update(PIP_NO_INDEX="1", PIP_DISABLE_PIP_VERSION_CHECK="1",
                          PYTHONDONTWRITEBYTECODE="1", SOURCE_DATE_EPOCH="1672560000")
        upstream = runpy.run_path(str(private / "generate.py"))
        args.output.mkdir(parents=True, exist_ok=True)
        upstream["ffi"].emit_c_code(str(args.output / "_nnpy.c"))
        shutil.copyfile(private / "nnpy/constants.py", args.output / "constants.py")
        # Compile the exact header bytes inspected by upstream generate.py. Its
        # generated C uses unqualified <nn.h> includes, as upstream setuptools does.
        for header in sorted(headers.glob("*.h")):
            target = args.output / "include/nanomsg" / header.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(header, target)
        sys.argv = ["setup.py", "egg_info"]
        runpy.run_path(str(private / "setup.py"), run_name="__main__")
        metadata = private / "nnpy.egg-info"
        expected = {"PKG-INFO", "SOURCES.txt", "dependency_links.txt", "requires.txt", "top_level.txt"}
        if {p.name for p in metadata.iterdir()} != expected:
            raise RuntimeError("Upstream setuptools metadata inventory changed")
        shutil.copytree(metadata, args.output / "nnpy-1.4.2.egg-info", dirs_exist_ok=True)
        receipt = {
            "schema": 1,
            "source_revision": "d8f260a176212bfe5f6626942c487b7d90842414",
            "sources": {name: digest(source / name) for name in names},
            "nanomsg_headers": {p.name: digest(p) for p in sorted(headers.glob("*.h"))},
            "nanomsg_library_sha256": digest(library),
            "nanomsg_soname": "libnanomsg.so.5",
            "generated": {name: digest(args.output / name) for name in ("_nnpy.c", "constants.py")},
        }
        (args.output / "generation.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
