"""Check declared Python/CFFI dependencies and the original compiled extension."""
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
archive, runtime = sys.argv[1:]
control = subprocess.check_output(["dpkg-deb", "--field", archive], text=True)
for field in ["Package: python3-libyang\n", "Version: 3.1.0-1\n", "python3-cffi", "libyang3", "python3 (>= 3.13~)", "python3 (<< 3.14)"]:
    assert field in control, control
assert "${" not in control, control
with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    subprocess.run(["dpkg-deb", "--control", archive, str(root / "control")], check=True)
    subprocess.run(["dpkg-deb", "--extract", archive, str(root / "data")], check=True)
    assert "py3compile" in (root / "control/postinst").read_text()
    assert "py3clean" in (root / "control/prerm").read_text()
    extensions = list((root / "data/usr/lib/python3/dist-packages").glob("_libyang.cpython-313-*.so"))
    assert len(extensions) == 1, extensions
    with tarfile.open(runtime) as original:
        member = next(item for item in original if item.name.removeprefix("./") == "usr/lib/python3/dist-packages/_libyang.so")
        assert extensions[0].read_bytes() == original.extractfile(member).read()
    assert (root / "data/usr/lib/python3/dist-packages/libyang-3.1.0.egg-info/PKG-INFO").is_file()
print(control)
