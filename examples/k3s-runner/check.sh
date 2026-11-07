#!/usr/bin/env bash
set -euo pipefail

. /etc/os-release
[[ "$ID" == debian && "$VERSION_CODENAME" == trixie ]]
[[ "$RUNNER_ARCH" == X64 && "$(uname -m)" == x86_64 ]]
export REGISTRY_CI_TEST_BAZEL=/usr/local/bin/bazel
bazel_version=$("$REGISTRY_CI_TEST_BAZEL" --version)
[[ "$bazel_version" == 'bazel 8.5.1' ]]

# The registry test builds a target in a fresh workspace and runs its Python
# program with several HOME settings, including a writable per-test directory.
python3 ci/tests/test_bazel_test_home.py -v

# Read the running interpreter's ELF header to verify the bundled guest
# actually executed an AArch64 binary (machine number 183).
guest=$(/usr/local/bin/sonic-arm64 -- /usr/bin/python3 -I -S -c '
import platform, sys
with open(sys.executable, "rb") as program:
    elf = program.read(20)
assert elf[:4] == b"\x7fELF" and int.from_bytes(elf[18:20], "little") == 183
assert platform.machine() == "aarch64"
print(f"ARM64 Python {platform.python_version()} under emulation")
')

printf 'Runner `%s` · %s (%s) · %s · %s\n' \
    "$RUNNER_NAME" "$PRETTY_NAME" "$RUNNER_ARCH" "$bazel_version" "$guest" \
    | tee -a "$GITHUB_STEP_SUMMARY"
