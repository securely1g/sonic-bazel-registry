#!/usr/bin/env python3
"""Build the maintained HTTP audit agent once, without downloaded build tools."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile


SOURCE_HASH_ENTRY = "META-INF/sonic-debian-http-audit.sha256"


def compiler_command() -> list[str]:
    javac = shutil.which("javac")
    if javac:
        return [javac]
    java = shutil.which("java")
    if java:
        # Some runner JRE packages retain jdk.compiler but omit the javac CLI.
        # Do not install a compiler or extract Bazel's embedded runtime here.
        return [java, "-m", "jdk.compiler/com.sun.tools.javac.Main"]
    raise RuntimeError("No system Java compiler is available")


def build(source: Path, output: Path) -> None:
    source = source.resolve(strict=True)
    if source.name != "DebianHttpAudit.java":
        raise ValueError("Expected maintained DebianHttpAudit.java source")
    source_bytes = source.read_bytes()
    with tempfile.TemporaryDirectory(prefix="debian-http-audit-build-") as temporary:
        work = Path(temporary)
        staged_source = work / source.name
        staged_source.write_bytes(source_bytes)
        classes = work / "classes"
        classes.mkdir()
        subprocess.run([*compiler_command(), "-source", "11", "-target", "11", "-Xlint:-options",
                        "-d", str(classes), str(staged_source)], check=True)
        compiled = sorted(classes.glob("DebianHttpAudit*.class"))
        if not (classes / "DebianHttpAudit.class").is_file():
            raise RuntimeError("Compiler did not produce the audit agent")
        for path in compiled:
            content = path.read_bytes()
            if content[:4] != b"\xca\xfe\xba\xbe" or int.from_bytes(content[6:8], "big") != 55:
                raise RuntimeError("Audit agent must use Java 11 class files")
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(prefix=".http-audit-", suffix=".jar", dir=output.parent,
                                         delete=False) as staged:
            staged_path = Path(staged.name)
        try:
            with zipfile.ZipFile(staged_path, "w", compression=zipfile.ZIP_DEFLATED) as jar:
                entries = {
                    "META-INF/MANIFEST.MF": b"Manifest-Version: 1.0\r\nPremain-Class: DebianHttpAudit\r\n\r\n",
                    SOURCE_HASH_ENTRY: hashlib.sha256(source_bytes).hexdigest().encode("ascii"),
                    **{path.name: path.read_bytes() for path in compiled},
                }
                for name, content in entries.items():
                    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                    info.compress_type = zipfile.ZIP_DEFLATED
                    info.external_attr = 0o100644 << 16
                    jar.writestr(info, content)
            staged_path.replace(output)
        finally:
            staged_path.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path(__file__).with_name("DebianHttpAudit.java"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build(args.source, args.output)


if __name__ == "__main__":
    main()
