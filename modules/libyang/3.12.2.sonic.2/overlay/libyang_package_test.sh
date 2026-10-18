#!/usr/bin/env bash
set -euo pipefail
runtime=$(realpath "$1")
debug=$(realpath "$2")
consumer=$(realpath "$3")
root="$TEST_TMPDIR/package"
mkdir -p "$root"
tar -xf "$runtime" -C "$root"
tar -xf "$debug" -C "$root"
mapfile -t libraries < <(find "$root/usr/lib" -name libyang.so.3.9.1)
[[ ${#libraries[@]} == 1 ]]
library=${libraries[0]}
[[ $(readlink "${library%/*}/libyang.so.3") == libyang.so.3.9.1 ]]
[[ $(readlink "${library%/*}/libyang.so") == libyang.so.3 ]]
readelf -d "$library" | grep -F 'Library soname: [libyang.so.3]'
# PCRE2 and xxHash are source-built static implementation dependencies.
! readelf -d "$library" | grep -E 'NEEDED.*(pcre2|xxhash)'
! nm -D --defined-only "$library" | grep -E ' (pcre2_|XXH)'
# The toolchain may emit DT_RPATH, which precedes LD_LIBRARY_PATH.
# Preloading the same SONAME forces this exact extracted ELF into the consumer.
LD_PRELOAD="$library" LD_LIBRARY_PATH="${library%/*}" "$consumer"
! readelf -S "$library" | grep -F '.debug_info'
build_id=$(readelf -n "$library" | sed -n 's/.*Build ID: //p')
[[ -n "$build_id" ]]
symbols="$root/usr/lib/debug/.build-id/${build_id:0:2}/${build_id:2}.debug"
[[ -f "$symbols" ]]
[[ $(readelf -n "$symbols" | sed -n 's/.*Build ID: //p') == "$build_id" ]]
readelf -S "$symbols" | grep -F '.debug_info'
objcopy --dump-section .gnu_debuglink="$TEST_TMPDIR/debuglink" "$library" "$TEST_TMPDIR/library"
python3 - "$TEST_TMPDIR/debuglink" "$symbols" <<'CHECK'
import pathlib, struct, sys, zlib
link = pathlib.Path(sys.argv[1]).read_bytes()
symbols = pathlib.Path(sys.argv[2])
name = link.split(b"\0", 1)[0].decode()
assert name == symbols.name, (name, symbols.name)
assert struct.unpack("<I", link[-4:])[0] == zlib.crc32(symbols.read_bytes())
CHECK
gdb -nx -batch -ex "set debug-file-directory $root/usr/lib/debug" -ex "file $library" -ex 'info line ly_ctx_new' > "$TEST_TMPDIR/gdb.txt"
cat "$TEST_TMPDIR/gdb.txt"
grep -E 'Line [0-9]+ of .*context.c' "$TEST_TMPDIR/gdb.txt"
