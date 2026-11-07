"""Compare public pkg-config outputs with the original Debian archive."""

import argparse
import hashlib
from pathlib import Path
import tarfile

parser = argparse.ArgumentParser()
parser.add_argument('--archive', required=True)
parser.add_argument('--triplet', required=True)
for group in ('direct', 'package', 'root'):
    parser.add_argument('--' + group, nargs='+', required=True)
args = parser.parse_args()
with tarfile.open(args.archive) as archive:
    expected = {}
    relocated = {}
    for member in archive.getmembers():
        if member.name.endswith('.pc') and (member.isfile() or member.issym() or member.islnk()):
            name = Path(member.name).name
            assert name not in expected, name
            expected[name] = archive.extractfile(member).read()
            installed = Path(member.name.lstrip("./"))
            # Debian's literal /usr installation prefix becomes relative to this
            # metadata file. All remaining bytes must match the archived file.
            depth = len(installed.parent.parts) - 1
            prefix = b"${pcfiledir}/" + b"/".join([b".."] * depth)
            relocated[name] = b"".join(
                b"prefix=" + prefix + b"\n" if line == b"prefix=/usr\n" else line
                for line in expected[name].splitlines(keepends=True)
            )
assert expected, 'The selected Debian package contains no pkg-config files'
assert any(args.triplet.encode() in content for content in expected.values()), expected.keys()
for group in ('direct', 'package', 'root'):
    paths = [Path(value) for value in getattr(args, group)]
    actual = {path.name: path.read_bytes() for path in paths}
    assert len(paths) == len(actual), (group, paths)
    assert actual == relocated, (group, actual.keys(), expected.keys())
print('Only installation prefixes relocate through direct, package and dependency-set targets; archive metadata remains original:')
for name, content in sorted(expected.items()):
    print(name, hashlib.sha256(content).hexdigest())
