#!/usr/bin/env bash
set -euo pipefail
export LC_ALL=C
trap 'echo "libnl3 package check failed at line $LINENO" >&2' ERR

consumer_source=$(realpath "$1")
shift
stems=(libnl-3 libnl-genl-3 libnl-route-3 libnl-nf-3 libnl-cli-3)
runtime_tars=()
dev_tars=()
debug_tars=()
multiarch=$(cc -print-multiarch)
case "$multiarch" in
    x86_64-linux-gnu|aarch64-linux-gnu) ;;
    *) echo "Unsupported native architecture: $multiarch" >&2; exit 1 ;;
esac
for archive in "${@:1:5}"; do runtime_tars+=("$(realpath "$archive")"); done
for archive in "${@:6:5}"; do dev_tars+=("$(realpath "$archive")"); done
for archive in "${@:11:5}"; do debug_tars+=("$(realpath "$archive")"); done
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
    libdir="$root/usr/lib/${multiarch}"
    library="$libdir/$stem.so.200.26.0"
    [[ -f "$library" && ! -L "$library" ]]
    check_library_link "$libdir/$stem.so.200" "$library"
    check_library_link "$libdir/$stem.so" "$library"
    [[ $(readelf -d "$library" | sed -n 's/.*Library soname: \[\(.*\)\]/\1/p') == "$stem.so.200" ]]
    [[ ! -e "$root/usr/include" ]]
    if [[ "$stem" == libnl-3 ]]; then
        [[ -f "$root/etc/libnl-3/classid" ]]
        [[ -f "$root/etc/libnl-3/pktloc" ]]
    fi
    tar -xf "${runtime_tars[$index]}" -C "$combined_root"
done

for index in "${!stems[@]}"; do
    stem=${stems[$index]}
    root="$TEST_TMPDIR/dev-$stem"
    mkdir -p "$root"
    tar -xf "${dev_tars[$index]}" -C "$root"
    includedir="$root/usr/include/libnl3"
    libdir="$root/usr/lib/${multiarch}"
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
    grep -Fxq 'libdir=${prefix}/lib/'"$multiarch" "$pkgconfig"
    grep -Fxq 'Cflags: -I${includedir}' "$pkgconfig"
done

# Compile against the extracted development package and execute its exact ELFs.
# Preloading avoids a toolchain DT_RPATH taking precedence over LD_LIBRARY_PATH.
route_root="$TEST_TMPDIR/dev-libnl-route-3"
route_libdir="$route_root/usr/lib/${multiarch}"
cc -std=c11 -Wall -Werror -I"$route_root/usr/include/libnl3" "$consumer_source" \
    -L"$route_libdir" -Wl,-rpath-link,"$route_libdir" -lnl-route-3 -lnl-3 -ldl \
    -o "$TEST_TMPDIR/package-consumer"
LIBNL3_EXPECTED_LIBRARY_DIR="$route_libdir" \
LD_PRELOAD="$route_libdir/libnl-3.so.200:$route_libdir/libnl-route-3.so.200" \
LD_LIBRARY_PATH="$route_libdir" "$TEST_TMPDIR/package-consumer"

# Load every shipped library and CLI plugin with immediate symbol resolution.
libdir="$combined_root/usr/lib/${multiarch}"
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

# Match detached symbols to every installed shared library and CLI plugin.
for index in "${!stems[@]}"; do
    symbol_root="$TEST_TMPDIR/debug-${stems[$index]}"
    mkdir -p "$symbol_root"
    tar -xf "${debug_tars[$index]}" -C "$symbol_root"
    python3 - "$TEST_TMPDIR/runtime-${stems[$index]}" "$symbol_root" <<'DEBUG'
import pathlib, re, struct, subprocess, sys, tempfile, zlib
runtime, symbols = map(pathlib.Path, sys.argv[1:])
elfs = [p for p in runtime.rglob('*') if p.is_file() and not p.is_symlink() and p.read_bytes()[:4] == b'\x7fELF']
assert elfs
for binary in elfs:
    notes = subprocess.check_output(['readelf', '-n', str(binary)], text=True)
    build_id = re.search(r'Build ID: ([0-9a-f]+)', notes).group(1)
    debug = symbols / 'usr/lib/debug/.build-id' / build_id[:2] / (build_id[2:] + '.debug')
    assert debug.is_file(), debug
    debug_notes = subprocess.check_output(['readelf', '-n', str(debug)], text=True)
    assert 'Build ID: ' + build_id in debug_notes
    runtime_sections = subprocess.check_output(['readelf', '-SW', str(binary)], text=True)
    debug_sections = subprocess.check_output(['readelf', '-SW', str(debug)], text=True)
    assert '.debug_info' not in runtime_sections
    assert '.debug_info' in debug_sections and '.debug_line' in debug_sections
    with tempfile.TemporaryDirectory() as directory:
        link = pathlib.Path(directory) / 'link'
        subprocess.run(['objcopy', '--dump-section', '.gnu_debuglink='+str(link), str(binary), str(pathlib.Path(directory)/'elf')], check=True)
        data = link.read_bytes(); end = data.index(b'\0')
        assert data[:end].decode() == debug.name
        assert struct.unpack_from('<I', data, (end+4)&~3)[0] == zlib.crc32(debug.read_bytes())
    output = subprocess.check_output(['gdb', '--batch', '--nx', '--quiet',
        '-ex', 'set debuginfod enabled off', '-ex', 'set debug-file-directory '+str(symbols/'usr/lib/debug'),
        '-ex', 'file '+str(binary), '-ex', 'info sources'], text=True, stderr=subprocess.STDOUT)
    # GDB lists partial compilation units before lazily reading their symbols.
    # Source paths prove the detached file was found; the line query below
    # then forces it to read actual DWARF line data.
    sources = re.findall(r'[^,\s]+/lib/[^,\s]+\.c(?=[,\s]|$)', output)
    assert sources, output
    output = subprocess.check_output(['gdb', '--batch', '--nx', '--quiet',
        '-ex', 'set debuginfod enabled off', '-ex', 'set debug-file-directory '+str(symbols/'usr/lib/debug'),
        '-ex', 'file '+str(binary), '-ex', 'info line '+sources[0]+':1'], text=True, stderr=subprocess.STDOUT)
    assert re.search(r'Line \d+ of .* (?:starts at address|is at address)', output), output
print('Validated detached symbols for', len(elfs), 'installed ELF files')
DEBUG
done
