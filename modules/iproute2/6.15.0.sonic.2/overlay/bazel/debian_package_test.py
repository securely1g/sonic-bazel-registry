"""Check actual source payload, dependency metadata and Debian maintainer scripts."""
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile

archive, runtime = sys.argv[1:]
control = subprocess.check_output(["dpkg-deb", "--field", archive], text=True)
for field in ["Package: iproute2\n", "Version: 6.15.0-1+sonic.0\n", "Provides: arpd\n", "Conflicts: arpd\n", "Breaks: iproute2-doc\n", "Replaces: iproute2-doc\n"]:
    assert field in control, control
assert "${" not in control and "debconf" in control and "libcap2-bin" in control, control
with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    subprocess.run(["dpkg-deb", "--control", archive, str(root / "control")], check=True)
    subprocess.run(["dpkg-deb", "--extract", archive, str(root / "data")], check=True)
    for name in ["config", "postinst", "postrm", "preinst", "prerm"]:
        script = root / "control" / name
        assert script.stat().st_mode & 0o111 == 0o111, name
        assert "#DEBHELPER#" not in script.read_text(), name
        subprocess.run(["/bin/sh", "-n", str(script)], check=True)
    assert "setcap" in (root / "control/postinst").read_text()
    assert "dpkg-maintscript-helper rm_conffile /etc/iproute2/rt_tables" in (root / "control/preinst").read_text()
    assert "iproute2/setcaps" in (root / "control/templates").read_text()
    with tarfile.open(runtime) as expected:
        for member in expected:
            target = root / "data" / member.name.removeprefix("./")
            if member.isfile():
                assert target.read_bytes() == expected.extractfile(member).read(), member.name
            elif member.issym():
                assert target.readlink().as_posix() == member.linkname, member.name
print(control)
