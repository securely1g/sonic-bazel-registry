#!/usr/bin/env bash
set -euo pipefail
runtime=$(realpath "$1")
debug=$(realpath "$2")
consumer=$(realpath "$3")
# Check the actual TAR against the source notices and complete model inventory.
python3 - "$runtime" "$4" "$5" "${@:6}" <<'PAYLOAD'
from pathlib import Path
import sys
import tarfile

runtime, copyright, changelog, *models = sys.argv[1:]
expected = {
    "usr/share/doc/libyang3/copyright": Path(copyright),
    "usr/share/doc/libyang3/changelog.Debian": Path(changelog),
}
assert len(models) == 8, models
expected.update({
    "usr/share/yang/modules/libyang/" + Path(model).name: Path(model)
    for model in models
})
assert len(expected) == 10, expected
assert Path(changelog).read_text().startswith("libyang (3.12.2-1) "), changelog
with tarfile.open(runtime) as archive:
    members = {member.name.removeprefix("./"): member for member in archive}
    assert all(member.uid == member.gid == 0 for member in members.values())
    installed_models = {
        name for name, member in members.items()
        if name.startswith("usr/share/yang/modules/libyang/") and member.isfile()
    }
    assert installed_models == {name for name in expected if name.endswith(".yang")}
    for name, source in expected.items():
        member = members[name]
        assert member.isfile() and member.mode == 0o644, (name, member.mode)
        assert archive.extractfile(member).read() == source.read_bytes(), name
    assert not any(name.startswith(("DEBIAN/", "var/lib/dpkg/")) for name in members)
print("Eight upstream models and Debian source notices match the runtime TAR")
PAYLOAD
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
