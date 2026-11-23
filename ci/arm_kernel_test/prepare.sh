#!/bin/bash
# Prepare the Linux AIO test's guest in this disposable runner.
set -euo pipefail
bundle=$1
scripts=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$bundle"
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
cd "$work"

fetch() {
    local output=$1 digest=$2 url
    shift 2
    for url in "$@"; do
        if curl --fail --location --silent --show-error --retry 2 --max-time 120 "$url" -o "$output" \
            && printf '%s  %s\n' "$digest" "$output" | sha256sum --check --status; then
            return 0
        fi
    done
    echo "Could not download $output with the expected SHA256" >&2
    return 1
}

kernel_path='pool/updates/main/l/linux-signed-arm64/linux-image-6.12.115+deb13.1-arm64_6.12.115-2_arm64.deb'
fetch kernel.deb 6a7ad2e34bfa57f943eaf59ecbca64baf64c4636634acfc0ebba04a476da5387 \
    "https://deb.debian.org/debian-security/$kernel_path" \
    "https://security.debian.org/debian-security/$kernel_path" \
    'https://snapshot.debian.org/file/37bff486a50bd36c79f13793bd3efb50c7615df2'
fetch busybox.deb c833be48abfa16bc19c4966ec93e289ff1ce5d2f1476cad3a57bd105378cd15c \
    'https://deb.debian.org/debian/pool/main/b/busybox/busybox-static_1.37.0-6+b9_arm64.deb' \
    'https://ftp.debian.org/debian/pool/main/b/busybox/busybox-static_1.37.0-6+b9_arm64.deb' \
    'https://snapshot.debian.org/file/6d31276d7d9ae8fd1fd27b9b368bef89e7677d62'

mkdir -p root/{dev,bin,lib/aarch64-linux-gnu}
dpkg-deb --fsys-tarfile kernel.deb | tar -xO ./boot/vmlinuz-6.12.115+deb13.1-arm64 > "$bundle/vmlinuz"
dpkg-deb --fsys-tarfile busybox.deb | tar -xO ./usr/bin/busybox > root/bin/busybox
chmod 755 root/bin/busybox
ln -s busybox root/bin/sh
install -m755 "$scripts/init" root/init
guestlibs=/opt/sonic-arm64-rootfs/usr/lib/aarch64-linux-gnu
install -m755 "$guestlibs/ld-linux-aarch64.so.1" root/lib/
install -m755 "$guestlibs/libc.so.6" root/lib/aarch64-linux-gnu/
(cd root && find . -print0 | cpio --null --format=newc --quiet -o) > "$bundle/base.cpio"
install -m755 "$scripts/executor" "$bundle/executor"
