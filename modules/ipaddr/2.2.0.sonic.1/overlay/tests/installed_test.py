"""Run the unchanged upstream suite against the installed Python payload."""
import importlib
import importlib.metadata
from pathlib import Path, PurePosixPath
import runpy
import sys
import tarfile
import tempfile

archive_path, upstream_test, source_path, license_path = map(Path, sys.argv[1:])
with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    with tarfile.open(archive_path) as archive:
        member = next(member for member in archive
                      if PurePosixPath(member.name).as_posix() ==
                      "usr/local/lib/python3.13/dist-packages/ipaddr.py")
        if (member.uid, member.gid, member.mode) != (0, 0, 0o644):
            raise AssertionError("installed Python module ownership/mode differs")
        if archive.extractfile(member).read() != source_path.read_bytes():
            raise AssertionError("installed module differs from fixed upstream source")
        archive.extractall(root, filter="data")
    site = root / "usr/local/lib/python3.13/dist-packages"
    sys.path.insert(0, str(site))
    module = importlib.import_module("ipaddr")
    if Path(module.__file__).resolve() != (site / "ipaddr.py").resolve():
        raise AssertionError("upstream tests did not import the installed payload")
    distribution = importlib.metadata.distribution("ipaddr")
    if distribution.version != "2.2.0" or distribution.requires:
        raise AssertionError("installed distribution identity/dependencies differ")
    license_file = site / "ipaddr-2.2.0.dist-info/licenses/COPYING"
    if license_file.read_bytes() != license_path.read_bytes():
        raise AssertionError("installed license differs from upstream COPYING")
    sys.argv = [str(upstream_test)]
    runpy.run_path(str(upstream_test), run_name="__main__")
