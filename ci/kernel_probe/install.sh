#!/bin/bash
set -euo pipefail
[[ $EUID == 0 ]]
source_dir=$(cd "$(dirname "$0")"; pwd)
install_dir=/opt/registry-ci-arm-kernel-probe
mkdir -p "$install_dir"
scratch=$(mktemp -d)
trap 'rm -rf "$scratch"' EXIT
cd "$scratch"
export DEBIAN_FRONTEND=noninteractive
dpkg --add-architecture arm64
apt-get -q -o Acquire::Retries=2 update
apt-get -q -y --no-install-recommends install qemu-system-arm:amd64 cpio
apt-get -q download linux-image-6.12.115+deb13.1-arm64:arm64=6.12.115-2 busybox-static:arm64=1:1.37.0-6+b9
kernel_deb=(linux-image-*.deb)
busybox_deb=(busybox-static_*.deb)
printf '%s  %s\n' 6a7ad2e34bfa57f943eaf59ecbca64baf64c4636634acfc0ebba04a476da5387 "${kernel_deb[0]}" \
    c833be48abfa16bc19c4966ec93e289ff1ce5d2f1476cad3a57bd105378cd15c "${busybox_deb[0]}" | sha256sum -c
dpkg-deb -x "${kernel_deb[0]}" unpacked
dpkg-deb -x "${busybox_deb[0]}" unpacked
install -m 644 unpacked/boot/vmlinuz-* "$install_dir/vmlinuz"
mkdir -p root/{dev,bin,lib/aarch64-linux-gnu}
busybox=$(find unpacked -path '*/bin/busybox' -type f -size +500k -print -quit)
install -m 755 "$busybox" root/bin/busybox
ln -s busybox root/bin/sh
install -m 755 "$source_dir/init" root/init
guestlibs=/opt/sonic-arm64-rootfs/usr/lib/aarch64-linux-gnu
install -m 755 "$guestlibs/ld-linux-aarch64.so.1" root/lib/
install -m 755 "$guestlibs/libc.so.6" root/lib/aarch64-linux-gnu/
mknod -m 600 root/dev/console c 5 1
mknod -m 666 root/dev/null c 1 3
(cd root; find . -print0 | cpio --null --format=newc --quiet -o) > "$install_dir/base.cpio"
install -m 755 "$source_dir/executor" "$install_dir/executor"
