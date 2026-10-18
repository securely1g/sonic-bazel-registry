"""Check the built DEB keeps its source payload and generated dependencies."""
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile

archive, runtime = map(Path, sys.argv[1:])
control = subprocess.check_output(["dpkg-deb", "--field", str(archive)], text=True)
assert "Package: socat\n" in control, control
assert "Version: 1.8.0.2-1\n" in control, control
assert "${" not in control, control
for dependency in ("libc6", "libreadline8t64", "libssl3t64", "libwrap0"):
    assert dependency in control, (dependency, control)
with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    subprocess.run(["dpkg-deb", "--extract", str(archive), str(root)], check=True)
    with tarfile.open(runtime) as expected:
        for member in expected:
            target = root / member.name.removeprefix("./")
            if member.isfile():
                assert target.read_bytes() == expected.extractfile(member).read(), member.name
            elif member.issym():
                assert target.is_symlink() and target.readlink().as_posix() == member.linkname, member.name
    assert (root / "usr/share/doc/socat/changelog.Debian").is_file()
print(control)
