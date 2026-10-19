"""Verify real package relationships, ABI metadata and Bazel-built payload."""
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile

archive, runtime = sys.argv[1:]
control = subprocess.check_output(["dpkg-deb", "--field", archive], text=True)
for field in ["Package: libyang3\n", "Version: 3.12.2-1\n", "Multi-Arch: same\n", "Breaks: libyang2, libyang2t64\n", "Replaces: libyang2, libyang2t64\n"]:
    assert field in control, control
assert "libc6" in control and "${" not in control, control
with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    subprocess.run(["dpkg-deb", "--control", archive, str(root / "control")], check=True)
    subprocess.run(["dpkg-deb", "--extract", archive, str(root / "data")], check=True)
    assert "ldconfig" in (root / "control/triggers").read_text()
    assert "libyang3 (>= 3.12.2)" in (root / "control/shlibs").read_text()
    with tarfile.open(runtime) as expected:
        for member in expected:
            path = member.name.removeprefix("./")
            target = root / "data" / path
            # The original runtime install manifest excludes developer links
            # and the TAR's SDK license location; Debian docs are added below.
            if path.endswith("libyang.so") or path == "usr/share/doc/libyang/copyright":
                assert not target.exists(), path
                continue
            if member.isfile():
                assert target.read_bytes() == expected.extractfile(member).read(), member.name
            elif member.issym():
                assert target.readlink().as_posix() == member.linkname, member.name
    assert (root / "data/usr/share/doc/libyang3/copyright").is_file()
    models = list((root / "data/usr/share/yang/modules/libyang").glob("*.yang"))
    assert len(models) == 8, models
    assert all(path.stat().st_mode & 0o777 == 0o644 for path in models)
print(control)
