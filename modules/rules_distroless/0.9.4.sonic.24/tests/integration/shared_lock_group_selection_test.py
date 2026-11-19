"""A group sharing a catalog must not acquire another group's package closure.

The catalog also serves Lua/libc groups; this group's independently reviewed root
is Architecture: all netbase. Its deliberately colliding name must remain usable.
"""
import sys
import tarfile

paths = sys.argv[1:]
assert len(paths) == 1, f"netbase-only group leaked other catalog packages: {paths}"
with tarfile.open(paths[0]) as archive:
    names = {member.name.lstrip("./") for member in archive}
assert "etc/services" in names
assert not any(name.endswith(".so") or ".so." in name for name in names)
print("PASS: independent root selection and collision-safe prepared catalog")
