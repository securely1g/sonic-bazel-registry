"""Import both extensions and run all upstream tests after the real wheel_layer."""
from email.parser import BytesParser
from pathlib import Path, PurePosixPath
import sys
import tarfile
import tempfile

from upstream_test import run_upstream


PREFIX = PurePosixPath("usr/local/lib/python3.13/dist-packages")


def main():
    with tempfile.TemporaryDirectory(prefix="bitarray-installed-") as directory:
        root = Path(directory)
        seen = set()
        total = 0
        with tarfile.open(sys.argv[1], "r:") as archive:
            for number, member in enumerate(archive):
                assert number < 128
                path = PurePosixPath(member.name)
                assert not path.is_absolute() and ".." not in path.parts
                if member.isdir():
                    assert path in PREFIX.parents or path == PREFIX or PREFIX in path.parents
                    continue
                assert member.isfile() and PREFIX in path.parents
                relative = path.relative_to(PREFIX)
                assert relative.parts[0] in ("bitarray", "bitarray-2.8.1.dist-info")
                assert member.name not in seen and member.mode == 0o644
                assert member.uid == member.gid == 0
                seen.add(member.name)
                total += member.size
                assert total <= 64 * 1024 * 1024
                target = root.joinpath(*relative.parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                stream = archive.extractfile(member)
                assert stream is not None
                data = stream.read(member.size + 1)
                assert len(data) == member.size
                with target.open("xb") as output:
                    output.write(data)
                target.chmod(0o644)
        assert len(seen) == 18
        assert (root / "bitarray-2.8.1.dist-info/INSTALLER").read_bytes() == b"sonic-build-infra\n"
        metadata = BytesParser().parsebytes((root / "bitarray-2.8.1.dist-info/METADATA").read_bytes())
        assert metadata["Name"] == "bitarray" and metadata["Version"] == "2.8.1"
        assert (root / "bitarray-2.8.1.dist-info/licenses/LICENSE").is_file()
        sys.path.insert(0, str(root))
        assert "bitarray" not in sys.modules
        if not run_upstream(expected_root=root):
            raise SystemExit(1)
        print("Both native extensions and the full upstream suite passed from the installed wheel layer")


if __name__ == "__main__":
    main()
