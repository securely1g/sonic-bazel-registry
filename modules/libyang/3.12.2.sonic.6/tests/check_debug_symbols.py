"""Verify source-line lookup from the delivered runtime and matching symbol TARs.

Run after registry_ci.py run, using the GDB explicitly installed by native CI.
The contract is inherited from .sonic.5's libyang_package_test.sh.
"""
import json
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import tempfile


def main():
    artifacts = Path(sys.argv[1]).resolve()
    outputs = json.loads((artifacts / "outputs.json").read_text())
    with tempfile.TemporaryDirectory(prefix="libyang-symbols-") as temporary:
        root = Path(temporary)
        for label in ("@libyang//:libyang_pkg", "@libyang//:libyang_pkg.debug_symbols"):
            archives = outputs[label]
            if len(archives) != 1:
                raise SystemExit("Expected one delivered archive for " + label)
            archive = (artifacts / archives[0]["path"]).resolve()
            if not archive.is_relative_to(artifacts):
                raise SystemExit("Archive must remain inside validation artifacts")
            with tarfile.open(archive) as source:
                source.extractall(root, filter="data")
        libraries = list(root.glob("usr/lib/*/libyang.so.3.9.1"))
        if len(libraries) != 1:
            raise SystemExit("Expected one installed libyang runtime library")
        result = subprocess.run(
            ["gdb", "-nx", "-batch", "-ex", "set debuginfod enabled off",
             "-ex", f"set debug-file-directory {root}/usr/lib/debug",
             "-ex", f"file {libraries[0]}", "-ex", "info line ly_ctx_new"],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
        (artifacts / "gdb-source-line.log").write_text(result.stdout)
        print(result.stdout, end="")
        if result.returncode or not re.search(r'Line [0-9]+ of .*context\.c', result.stdout):
            raise SystemExit("Delivered debug symbols do not resolve ly_ctx_new to context.c")


if __name__ == "__main__":
    main()
