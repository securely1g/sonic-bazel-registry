#!/usr/bin/env bash
# Run the Linux AIO regression on an ARM kernel in the AMD64 pilot pod.
set -euo pipefail

kit=/usr/local/lib/sonic-pilot-arm-kernel
if [[ ${1:-} == --prepare ]]; then
    guest=$2
    apt-get -o APT::Update::Error-Mode=any update
    apt-get install -y --no-install-recommends qemu-system-arm
    mkdir -p "$guest$kit/amd64"
    emulator=$(command -v qemu-system-aarch64)
    install -m 0755 "$emulator" "$guest$kit/amd64/"
    # Invoke AMD64 QEMU with its own loader and libraries from the ARM root.
    # This keeps the full-system emulator within the same job's CPU/memory limit.
    ldd "$emulator" | awk '/=> \// { print $3 } /^[[:space:]]*\// { print $1 }' |
        while read -r library; do cp -L "$library" "$guest$kit/amd64/"; done

    # Debian linux-image-6.12.115+deb13.1-cloud-arm64, version 6.12.115-2.
    package="$RUNNER_TEMP/pilot-arm-kernel.deb"
    curl --fail --location --retry 3 --output "$package" \
        https://snapshot.debian.org/file/3c963928c1b2e186c607db5e2d50d8c47686abc0
    printf '%s  %s\n' 4ef23dda49241aef1718ef05cb4107733b4eb35b5245eb8ea76788f3a8052567 "$package" |
        sha256sum --check --strict
    dpkg-deb --fsys-tarfile "$package" |
        tar -xO ./boot/vmlinuz-6.12.115+deb13.1-cloud-arm64 > "$guest$kit/vmlinuz"
    install -m 0755 "$0" "$guest/usr/local/bin/sonic-pilot-arm-kernel-test"
    exit 0
fi

# Bazel supplies TEST_TARGET to each test. Keep every other test's original
# executable, arguments, and exit status, including the other distroless tests.
if [[ ! ${TEST_TARGET:-} =~ ^@@?rules_distroless\+?//registry_ci:linux_headers_test$ ]]; then
    exec "$@"
fi
binary=$1
shift
tree=$(mktemp -d "${TEST_TMPDIR:-/tmp}/arm-kernel.XXXXXXXX")
trap 'rm -rf "$tree"' EXIT
mkdir -p "$tree/root/bin" "$tree/root/lib/aarch64-linux-gnu"
install -m 0755 "$binary" "$tree/root/test"
cp /usr/bin/busybox "$tree/root/bin/"
cp -L /lib/ld-linux-aarch64.so.1 "$tree/root/lib/"
cp -L /lib/aarch64-linux-gnu/libc.so.6 "$tree/root/lib/aarch64-linux-gnu/"
{
    echo '#!/bin/busybox sh'
    echo 'printf "ARM test kernel: "; /bin/busybox uname -srm'
    python3 -c 'import shlex, sys; print(shlex.join(["/test", *sys.argv[1:]]))' "$@"
    echo 'printf "SONIC_ARM_KERNEL_TARGET_EXIT=%s\n" "$?"'
    echo 'exec /bin/busybox poweroff -f'
} > "$tree/root/init"
chmod 0755 "$tree/root/init"
(cd "$tree/root" && find . -print0 | cpio --quiet --null -o -H newc | gzip -1) > "$tree/initrd"
printf 'Full-system ARM test %s\n' "$TEST_TARGET"
"$kit/amd64/ld-linux-x86-64.so.2" --library-path "$kit/amd64" "$kit/amd64/qemu-system-aarch64" \
    -machine virt,accel=tcg -cpu cortex-a57 -smp 1 -m 256 -nodefaults -nographic \
    -serial stdio -monitor none -no-reboot -kernel "$kit/vmlinuz" -initrd "$tree/initrd" \
    -append 'console=ttyAMA0 rdinit=/init panic=1 loglevel=4' | tee "$tree/console"
mapfile -t results < <(tr -d '\r' < "$tree/console" | sed -n 's/^SONIC_ARM_KERNEL_TARGET_EXIT=\([0-9]\{1,3\}\)$/\1/p')
if (( ${#results[@]} != 1 )) || (( results[0] > 255 )); then
    echo 'The guest did not report one valid target exit status' >&2
    exit 1
fi
exit "${results[0]}"
