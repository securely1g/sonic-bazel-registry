#!/bin/bash
# Diagnostic branch only. The manager repository and worker image are private.
# A maintainer provides these five files from its reviewed image to this one
# disposable runner. The production registry entry contains no installation step.
set -euo pipefail
input="$RUNNER_TEMP/fips-worker-inputs-$GITHUB_RUN_ID-$GITHUB_RUN_ATTEMPT"
mkdir -p "$input"
printf 'Awaiting private worker image inputs in %s\n' "$input"
for (( n=0; n<240; n++ )); do
    if [[ -f "$input/ready" ]]; then break; fi
    sleep 5
done
[[ -f "$input/ready" ]] || { echo "Missing reviewed worker image inputs" >&2; exit 1; }
cd "$input"
sha256sum --check --strict <<'EXPECTED'
0d051f9e2f71c04234afa9b9f8a993f2d6189aedbd3610ab68e4610f16f7e1b1  sonic-arm64
c5c8ef0ea592b44364b593f62d9a83800212fa820bbe2c3caa419f2364b86a93  sonic-arm64-kernel
58fd41ad2062adfc02d8fc0d3cf619b1113992550a00861926b1b6acb755f04a  sonic-proot
9c37ace54ef7e1919411fd912e9f34d6982ddd7f4c8ef3c8aee56f4c4d70db67  kernel
6b4d9e476bce37dd8283035a9b1297e8e939c9aea94b56f2420cc5618802cfd4  initrd.gz
EXPECTED
fetch() {
    curl --fail --show-error --silent --location --retry 3 "$1" -o "$2"
    printf '%s  %s\n' "$3" "$2" | sha256sum --check --strict
}
fetch 'https://deb.debian.org/debian/pool/main/libz/libzstd/libzstd-dev_1.5.7+dfsg-1_arm64.deb' zstd-dev.deb 05cf42de5c9fdf17f49f663b47bfe736f10fbc7080fcc3a86ac43d5d670de149
fetch 'https://deb.debian.org/debian/pool/main/z/zlib/zlib1g-dev_1.3.dfsg+really1.3.1-1+b1_arm64.deb' zlib-dev.deb 745ebcf1fa115e230af76216355d7290a24f1790fe3780249b519c0e4d30534f
sudo -n apt-get -o APT::Update::Error-Mode=any update
sudo -n apt-get install -y --no-install-recommends qemu-system-arm
sudo -n install -D -m755 sonic-proot /usr/local/libexec/sonic-proot
sudo -n install -m755 sonic-arm64 sonic-arm64-kernel /usr/local/bin/
sudo -n install -d /usr/local/share/sonic-arm64-kernel
sudo -n install -m644 kernel initrd.gz /usr/local/share/sonic-arm64-kernel/
sudo -n /usr/local/bin/sonic-arm64 --bind "$input" -- /usr/bin/dpkg --install "$input/zstd-dev.deb" "$input/zlib-dev.deb"
sudo -n /usr/local/bin/sonic-arm64 -- /usr/bin/dpkg-query -W libzstd-dev zlib1g-dev
/usr/local/bin/sonic-arm64-kernel --timeout 90 -- /usr/bin/uname -rm
