"""Check source-built library packages carry installable ABI metadata."""
from pathlib import Path
import subprocess
import sys
import tempfile

for archive in sys.argv[1:]:
    control = subprocess.check_output(["dpkg-deb", "--field", archive], text=True)
    assert "Version: 3.7.0-0.2+b1sonic1\n" in control, control
    assert "Multi-Arch: same\n" in control, control
    assert "${" not in control, control
    package = next(line[9:] for line in control.splitlines() if line.startswith("Package: "))
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        subprocess.run(["dpkg-deb", "--control", archive, str(root / "control")], check=True)
        subprocess.run(["dpkg-deb", "--extract", archive, str(root / "data")], check=True)
        assert (root / "data/usr/share/doc" / package / "changelog.Debian").is_file()
        if package.endswith("-200"):
            assert "ldconfig" in (root / "control/triggers").read_text()
            assert package in (root / "control/shlibs").read_text()
            assert package in (root / "control/symbols").read_text()
            assert "libc6" in control
        else:
            assert "(= 3.7.0-0.2+b1sonic1)" in control
        if package == "libnl-3-200":
            conffiles = (root / "control/conffiles").read_text().splitlines()
            assert set(conffiles) == {"/etc/libnl-3/classid", "/etc/libnl-3/pktloc"}, conffiles
            assert not list((root / "data").glob("usr/lib/*/libnl-3.so"))
    print(control)
