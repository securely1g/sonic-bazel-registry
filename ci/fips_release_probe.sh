#!/bin/bash
# Diagnostic branch only. Install the pending manager image's runtime in this
# disposable CI container so the immutable production registry entry can run.
set -euo pipefail
work="$RUNNER_TEMP/fips-reviewed-runner"
mkdir -p "$work"/{sources/arm-kernel,proot-src,binaries}
cd "$work"
fetch() {
    local url=$1 dest=$2 sha=$3
    curl --fail --show-error --silent --location --retry 3 "$url" -o "$dest"
    printf '%s  %s\n' "$sha" "$dest" | sha256sum --check --strict
}
manager_rev=6b032f9f1ba9f8e3d7c6d7b0dadbfa8f347a24f7
base="https://raw.githubusercontent.com/securely1g/agi-projects/$manager_rev/sonic-slave-wrk-mgr/registry-runner"
fetch "$base/arm-kernel/build" "sources/arm-kernel/build" f4a79a1d946ec4ee8a50143271560df9bb4ad865a1f08fc5f439988aa6591348
fetch "$base/arm-kernel/init" "sources/arm-kernel/init" 3b656fc33754f0425b97adb3265561aca6fa59e7dfd1c7138d4cdefd16a7bb78
fetch "$base/arm-kernel/exec" "sources/arm-kernel/exec" c5c8ef0ea592b44364b593f62d9a83800212fa820bbe2c3caa419f2364b86a93
fetch "$base/arm64-exec" "sources/arm64-exec" 0d051f9e2f71c04234afa9b9f8a993f2d6189aedbd3610ab68e4610f16f7e1b1
fetch "$base/proot-exec-string-limit.patch" "sources/proot-exec-string-limit.patch" 20410a5998656b8666cdb47be80dcee0c3648c3a55a9e30795041b217cca9e38
fetch https://codeload.github.com/proot-me/proot/tar.gz/25dc6a3134891f98a79f57ce1c2c1b23ff15cad1 proot.tar.gz 6adb0d808dad47d66f503d6d5a699b455ac1a0a519b905378be4ffc0af92f40e
fetch https://codeload.github.com/proot-me/uthash/tar.gz/e493aa90a2833b4655927598f169c31cfcdf7861 uthash.tar.gz 2ddb6665e82ffd7e87a27b97081bddf8f09520b7a2cfd6ab011541e7cde991fa
fetch 'https://deb.debian.org/debian/pool/main/l/linux-signed-arm64/linux-image-6.12.107+deb13-arm64_6.12.107-1_arm64.deb' kernel.deb 20c92f3f97dd466e0400a6fcb792bde85af842fbb5e8b471370065e3de9d9fc9
fetch 'https://deb.debian.org/debian/pool/main/b/busybox/busybox-static_1.37.0-6+b9_arm64.deb' busybox.deb c833be48abfa16bc19c4966ec93e289ff1ce5d2f1476cad3a57bd105378cd15c
fetch 'https://deb.debian.org/debian/pool/main/libz/libzstd/libzstd-dev_1.5.7+dfsg-1_arm64.deb' zstd-dev.deb 05cf42de5c9fdf17f49f663b47bfe736f10fbc7080fcc3a86ac43d5d670de149
fetch 'https://deb.debian.org/debian/pool/main/z/zlib/zlib1g-dev_1.3.dfsg+really1.3.1-1+b1_arm64.deb' zlib-dev.deb 745ebcf1fa115e230af76216355d7290a24f1790fe3780249b519c0e4d30534f
sudo -n apt-get -o APT::Update::Error-Mode=any update
sudo -n apt-get install -y --no-install-recommends qemu-system-arm kmod cpio libtalloc-dev
tar -xf proot.tar.gz --strip-components=1 -C proot-src
tar -xf uthash.tar.gz --strip-components=1 -C proot-src/lib/uthash
patch -d proot-src -p1 < sources/proot-exec-string-limit.patch
make -s -C proot-src/src -j2 WITHOUT_PYTHON=1 proot
sudo -n install -D -m755 proot-src/src/proot /usr/local/libexec/sonic-proot
sudo -n install -m755 sources/arm64-exec /usr/local/bin/sonic-arm64
sudo -n /usr/local/bin/sonic-arm64 --bind "$work" -- /usr/bin/dpkg --install "$work/zstd-dev.deb" "$work/zlib-dev.deb"
sudo -n /usr/local/bin/sonic-arm64 -- /usr/bin/dpkg-query -W libzstd-dev zlib1g-dev
bash sources/arm-kernel/build "$work/kernel.deb" "$work/busybox.deb" "$work/binaries"
sudo -n install -d /usr/local/share/sonic-arm64-kernel
sudo -n install -m644 binaries/kernel binaries/initrd.gz /usr/local/share/sonic-arm64-kernel/
sudo -n install -m755 sources/arm-kernel/exec /usr/local/bin/sonic-arm64-kernel
/usr/local/bin/sonic-arm64-kernel --timeout 90 -- /usr/bin/uname -rm
