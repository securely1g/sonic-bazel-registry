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
    for member in archive.getmembers():
        if member.name.endswith('.pc') and (member.isfile() or member.issym() or member.islnk()):
            name = Path(member.name).name
            assert name not in expected, name
            expected[name] = archive.extractfile(member).read()
assert expected, 'The selected Debian package contains no pkg-config files'
assert any(args.triplet.encode() in content for content in expected.values()), expected.keys()
for group in ('direct', 'package', 'root'):
    paths = [Path(value) for value in getattr(args, group)]
    actual = {path.name: path.read_bytes() for path in paths}
    assert len(paths) == len(actual), (group, paths)
    assert actual == expected, (group, actual.keys(), expected.keys())
print('Original metadata is unchanged through direct, package and dependency-set targets:')
for name, content in sorted(expected.items()):
    print(name, hashlib.sha256(content).hexdigest())
