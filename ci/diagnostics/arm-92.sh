#!/bin/bash
set -euo pipefail

work="$RUNNER_TEMP/iproute2-arm-executor"
mkdir -p "$work"/{src,talloc,bin}
cd "$work"
fetch() {
    curl --fail --show-error --silent --location --retry 3 "$1" -o "$2"
    printf '%s  %s\n' "$3" "$2" | sha256sum --check --status
}
fetch https://codeload.github.com/proot-me/proot/tar.gz/25dc6a3134891f98a79f57ce1c2c1b23ff15cad1 proot.tar.gz 6adb0d808dad47d66f503d6d5a699b455ac1a0a519b905378be4ffc0af92f40e
fetch https://codeload.github.com/proot-me/uthash/tar.gz/e493aa90a2833b4655927598f169c31cfcdf7861 uthash.tar.gz 2ddb6665e82ffd7e87a27b97081bddf8f09520b7a2cfd6ab011541e7cde991fa
fetch 'https://deb.debian.org/debian/pool/main/s/samba/libtalloc-dev_2.4.3+samba4.22.11+dfsg-0+deb13u1_amd64.deb' talloc.deb c415d6e45ce02e30099198dedc39afba1057d7c00bebcdb2735c23399e4df8e7
tar -xf proot.tar.gz --strip-components=1 -C src
tar -xf uthash.tar.gz --strip-components=1 -C src/lib/uthash
dpkg-deb -x talloc.deb talloc
ln -s /usr/lib/x86_64-linux-gnu/libtalloc.so.2.4.3 talloc/usr/lib/x86_64-linux-gnu/libtalloc.so.2.4.3
export PKG_CONFIG_PATH="$work/talloc/usr/lib/x86_64-linux-gnu/pkgconfig" PKG_CONFIG_SYSROOT_DIR="$work/talloc"

python3 - <<'PY'
from pathlib import Path
p = Path('src/src/execve/aoxp.c')
s = p.read_text()
old = 'if (status >= ARG_MAX)\n\treturn -ENOMEM;'
assert s.count(old) == 1
p.write_text(s.replace(old, 'if (status > ARG_MAX)\n\treturn -E2BIG;'))
PY
make -s -C src/src -j2 WITHOUT_PYTHON=1 proot
install -m755 src/src/proot bin/proot
python3 - <<'PY'
from pathlib import Path
p = Path('bin/sonic-arm64')
s = Path('/usr/local/bin/sonic-arm64').read_text()
old = 'PROOT = "/usr/bin/proot"'
assert s.count(old) == 1
p.write_text(s.replace(old, f'PROOT = "{p.with_name("proot").resolve()}"'))
p.chmod(0o755)
PY
printf 'ARM_TEST_EXECUTOR=%s/bin/sonic-arm64\n' "$work" >> "$GITHUB_ENV"
