"""Original dbgsym handoff: matching build IDs, separate usable DWARF."""
import pathlib
import sys
import tarfile
import zlib

from elf_metadata import Elf

# rules/lm-sensors.mk exports these three dbgsym packages. Debian splits
# every ELF of each selected package, including the two dump utilities.
installed = {
    "libsensors5": ["usr/lib/x86_64-linux-gnu/libsensors.so.5.0.0"],
    "lm-sensors": ["usr/bin/sensors", "usr/sbin/isadump", "usr/sbin/isaset"],
    "sensord": ["usr/sbin/sensord"],
}
for (package, paths), runtime_path, debug_path in zip(
    installed.items(), sys.argv[1::2], sys.argv[2::2], strict=True
):
    with tarfile.open(runtime_path) as runtime, tarfile.open(debug_path) as debug:
        runtime_members = {m.name.removeprefix("./"): m for m in runtime}
        debug_files = {
            m.name.removeprefix("./"): debug.extractfile(m).read()
            for m in debug if m.isfile()
        }
        expected = set()
        for path in paths:
            elf = Elf(runtime.extractfile(runtime_members[path]).read())
            assert elf.build_id, (package, path, "missing build ID")
            debug_name = "usr/lib/debug/.build-id/" + elf.build_id[:2] + "/" + elf.build_id[2:] + ".debug"
            expected.add(debug_name)
            debug_bytes = debug_files[debug_name]
            dwarf = Elf(debug_bytes)
            assert dwarf.build_id == elf.build_id, (package, path, "build ID mismatch")
            assert elf.debuglink == pathlib.PurePosixPath(debug_name).name
            assert elf.debuglink_crc == zlib.crc32(debug_bytes)
            assert any(name in dwarf.by_name and dwarf.by_name[name][5] > 0 for name in (".debug_info", ".zdebug_info")), (package, path, "empty DWARF")
            assert not any(name in elf.by_name for name in (".debug_info", ".zdebug_info")), (package, path, "runtime contains DWARF")
            if package == "libsensors5":
                assert elf.soname == "libsensors.so.5"
        assert set(debug_files) == expected, (package, set(debug_files), expected)
