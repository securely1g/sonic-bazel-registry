#!/usr/bin/python3
"""Run the nested rules_go test workspace with the outer build's ARM toolchain."""
import subprocess
import sys
from pathlib import Path

binary = "/usr/local/lib/registry-ci-native-bazel"
args = sys.argv[1:]
if not any(command in args for command in ("build", "cquery")):
    raise SystemExit(subprocess.call([binary, *args]))
index = next(i for i, argument in enumerate(args) if argument in ("build", "cquery"))
prefix = [binary, "--batch", "--host_jvm_args=-Xmx1024m", *args[:index]]
command, rest = args[index], args[index+1:]
options = [
    "--inject_repository=registry_ci_cross_cc=__ADAPTER__",
    "--extra_toolchains=@registry_ci_cross_cc//:toolchain",
    "--platforms=@registry_ci_cross_cc//:nested_arm64",
    "--host_platform=@registry_ci_cross_cc//:nested_amd64",
    "--extra_execution_platforms=@registry_ci_cross_cc//:nested_amd64",
    "--jobs=2", "--spawn_strategy=local",
    "--experimental_downloader_config=__MIRRORS__",
]
subprocess.run([*prefix, command, *options, *rest], check=True)
if command == "build":
    files = subprocess.check_output([*prefix, "cquery", "--output=files", *options, *rest], text=True)
    paths = [Path(line) for line in files.splitlines() if line]
    if not paths:
        sys.exit("Nested build produced no outputs")
    for path in paths:
        with path.open("rb") as stream:
            header = stream.read(20)
        if not (header[:6] == b"\x7fELF\x02\x01" and int.from_bytes(header[18:20], "little") == 183):
            sys.exit(f"Nested output is not an AArch64 ELF: {path}")
        print(f"Nested AArch64 ELF verified: {path}", file=sys.stderr)
