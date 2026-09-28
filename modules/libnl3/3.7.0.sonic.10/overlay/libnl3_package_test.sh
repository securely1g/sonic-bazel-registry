#!/usr/bin/env bash
set -euo pipefail
export LC_ALL=C
trap 'echo "libnl3 package check failed at line $LINENO" >&2' ERR

consumer_source=$(realpath "$1")
shift
stems=(libnl-3 libnl-genl-3 libnl-route-3 libnl-nf-3 libnl-cli-3)
runtime_tars=()
dev_tars=()
for archive in "${@:1:5}"; do runtime_tars+=("$(realpath "$archive")"); done
for archive in "${@:6:5}"; do dev_tars+=("$(realpath "$archive")"); done
combined_root="$TEST_TMPDIR/runtime"
mkdir -p "$combined_root"

check_library_link() {
    local link=$1 library=$2 target
    [[ -L "$link" ]]
    target=$(readlink "$link")
    [[ "$target" != /* ]]
    [[ $(realpath "$link") == "$(realpath "$library")" ]]
}

for index in "${!stems[@]}"; do
    stem=${stems[$index]}
    root="$TEST_TMPDIR/runtime-$stem"
    mkdir -p "$root"
    tar -xf "${runtime_tars[$index]}" -C "$root"
    libdir="$root/usr/lib/x86_64-linux-gnu"
    library="$libdir/$stem.so.200"
    [[ -f "$library" && ! -L "$library" ]]
    check_library_link "$libdir/$stem.so" "$library"
    [[ $(readelf -d "$library" | sed -n 's/.*Library soname: \[\(.*\)\]/\1/p') == "$stem.so.200" ]]
    [[ ! -e "$root/usr/include" ]]
    tar -xf "${runtime_tars[$index]}" -C "$combined_root"
done

for index in "${!stems[@]}"; do
    stem=${stems[$index]}
    root="$TEST_TMPDIR/dev-$stem"
    mkdir -p "$root"
    tar -xf "${dev_tars[$index]}" -C "$root"
    includedir="$root/usr/include/libnl3"
    libdir="$root/usr/lib/x86_64-linux-gnu"
    [[ -f "$includedir/netlink/netlink.h" ]]
    [[ -f "$includedir/netlink/route/route.h" ]]
    [[ ! -e "$root/usr/include/linux" ]]
    [[ ! -e "$includedir/linux" ]]
    [[ ! -e "$includedir/linux-private" ]]
    [[ ! -e "$includedir/netlink-private" ]]
    [[ -f "$libdir/$stem.so.200" ]]
    check_library_link "$libdir/$stem.so" "$libdir/$stem.so.200"
    pkgconfig="$libdir/pkgconfig/$stem.0.pc"
    grep -Fxq 'includedir=${prefix}/include/libnl3' "$pkgconfig"
    grep -Fxq 'libdir=${prefix}/lib/x86_64-linux-gnu' "$pkgconfig"
    grep -Fxq 'Cflags: -I${includedir}' "$pkgconfig"
done

# Compile against the extracted development package and execute its exact ELFs.
# Preloading avoids a toolchain DT_RPATH taking precedence over LD_LIBRARY_PATH.
route_root="$TEST_TMPDIR/dev-libnl-route-3"
route_libdir="$route_root/usr/lib/x86_64-linux-gnu"
cc -std=c11 -Wall -Werror -I"$route_root/usr/include/libnl3" "$consumer_source" \
    -L"$route_libdir" -Wl,-rpath-link,"$route_libdir" -lnl-route-3 -lnl-3 -ldl \
    -o "$TEST_TMPDIR/package-consumer"
LIBNL3_EXPECTED_LIBRARY_DIR="$route_libdir" \
LD_PRELOAD="$route_libdir/libnl-3.so.200:$route_libdir/libnl-route-3.so.200" \
LD_LIBRARY_PATH="$route_libdir" "$TEST_TMPDIR/package-consumer"

# Load every shipped library and CLI plugin with immediate symbol resolution.
libdir="$combined_root/usr/lib/x86_64-linux-gnu"
preload="$libdir/libnl-3.so.200:$libdir/libnl-genl-3.so.200:$libdir/libnl-route-3.so.200:$libdir/libnl-nf-3.so.200:$libdir/libnl-cli-3.so.200"
LD_PRELOAD="$preload" LD_LIBRARY_PATH="$libdir" python3 - "$libdir" <<'CHECK'
import ctypes
import os
import pathlib
import sys

root = pathlib.Path(sys.argv[1]).resolve()
expected_plugins = {
    "cls/basic.so", "cls/cgroup.so", "qdisc/bfifo.so", "qdisc/blackhole.so",
    "qdisc/fq_codel.so", "qdisc/hfsc.so", "qdisc/htb.so", "qdisc/ingress.so",
    "qdisc/pfifo.so", "qdisc/plug.so",
}
plugin_root = root / "libnl-3/cli"
plugins = sorted(plugin_root.rglob("*.so"))
assert {path.relative_to(plugin_root).as_posix() for path in plugins} == expected_plugins
libraries = sorted(root.glob("libnl-*.so.200"))
assert len(libraries) == 5
handles = [ctypes.CDLL(str(path), mode=os.RTLD_NOW | os.RTLD_LOCAL) for path in libraries + plugins]
mapped = {
    pathlib.Path(line.split()[-1]).resolve()
    for line in pathlib.Path("/proc/self/maps").read_text().splitlines()
    if "/" in line.split()[-1] and "libnl" in pathlib.Path(line.split()[-1]).name
}
assert mapped and all(path.is_relative_to(root) for path in mapped), mapped
assert all(path.resolve() in mapped for path in libraries), mapped
CHECK
