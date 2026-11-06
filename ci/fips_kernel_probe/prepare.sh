#!/bin/bash
# Prepare the pinned ARM kernel and minimal initramfs for the AF_ALG diagnostic.
set -euo pipefail
out=$1
mkdir -p "$out/packages" "$out/extracted" "$out/initroot/init-tools" "$out/initroot/modules"
fetch() {
    local name=$1 path=$2 sha=$3
    local deb="$out/packages/$name.deb"
    if ! printf '%s  %s\n' "$sha" "$deb" | sha256sum --check --status; then
        for mirror in https://deb.debian.org/debian https://ftp.debian.org/debian; do
            if curl --fail --silent --show-error --location --retry 3 --output "$deb" "$mirror/$path" &&
                printf '%s  %s\n' "$sha" "$deb" | sha256sum --check --status; then break; fi
        done
    fi
    printf '%s  %s\n' "$sha" "$deb" | sha256sum --check --strict
    dpkg-deb -x "$deb" "$out/extracted"
}
version=6.12.107+deb13-arm64
fetch kernel pool/main/l/linux-signed-arm64/linux-image-6.12.107+deb13-arm64_6.12.107-1_arm64.deb 20c92f3f97dd466e0400a6fcb792bde85af842fbb5e8b471370065e3de9d9fc9
fetch busybox pool/main/b/busybox/busybox-static_1.37.0-6+b9_arm64.deb c833be48abfa16bc19c4966ec93e289ff1ce5d2f1476cad3a57bd105378cd15c
install -m 644 "$out/extracted/boot/vmlinuz-$version" "$out/kernel"
install -m 755 "$out/extracted/usr/bin/busybox" "$out/initroot/init-tools/busybox"
install -m 755 "$(dirname "$0")/init" "$out/initroot/init"
# The split Debian kernel package uses the merged-/usr layout of a full root.
if [[ ! -e "$out/extracted/lib" ]]; then ln -s usr/lib "$out/extracted/lib"; fi
depmod -b "$out/extracted" "$version"
for module in 9pnet_virtio 9p algif_skcipher; do
    modprobe -d "$out/extracted" -S "$version" --show-depends "$module"
done | awk '$1 == "insmod" && !seen[$2]++ {print $2}' > "$out/modules"
: > "$out/initroot/modules/order"
while IFS= read -r path; do
    name=$(basename "$path" .xz)
    xz -dc "$path" > "$out/initroot/modules/$name"
    printf '%s\n' "$name" >> "$out/initroot/modules/order"
done < "$out/modules"
(cd "$out/initroot"; find . -print0 | cpio --quiet --null -o --format=newc | gzip -1) > "$out/initrd.gz"
