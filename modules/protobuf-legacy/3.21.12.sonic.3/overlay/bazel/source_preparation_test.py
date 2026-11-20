"""Compare fetched source with Debian's independently extracted source package.

Expected digests come from dpkg-source extraction of the checksum-pinned
protobuf 3.21.12-11+deb13u1 archives, before the Bazel integration overlay.
They cover file names, bytes and executable bits, not extraction timestamps.
"""

import argparse
import hashlib
import json
from pathlib import Path
import shlex


SOURCE_DIGEST = "3b978f0bdcd5b72c4495452d4a44b3dfdc2bbceb2a717b3eca14d7f0a20af4f7"
PATCH_DIGEST = "c9a85e35df54acd3e005ddd3a317324afb97862688b8a6e864ffe24997341785"
METADATA = {
    "control": "16b051eaf329ae7cabc59b03ee447d0d468ebd6a1a34a04b8fadef603299770f",
    "changelog": "6d17884cc6ef7c85da0d4d335e7b2af4fe8ed8bb11750581c29de12d6beda8a2",
    "copyright": "77ae762c8b3aa11e07a48184818111d28e2274229a8eb121e19477d1a40f3b76",
}


def digest(root, paths):
    records = [
        [str(path.relative_to(root)), bool(path.stat().st_mode & 0o111),
         hashlib.sha256(path.read_bytes()).hexdigest()]
        for path in sorted(paths)
    ]
    return hashlib.sha256(json.dumps(records, separators=(",", ":")).encode()).hexdigest()


def verify(root):
    series = root / "debian/patches/series"
    patches = []
    for line in series.read_text().splitlines():
        words = shlex.split(line, comments=True)
        if words:
            patches.append(series.parent / words[0])
    assert len(patches) == 32, "Incomplete Debian patch series"
    assert digest(root, [series, *patches]) == PATCH_DIGEST, "Original Debian series changed"

    sources = [
        path
        for directory in ["src", "python"]
        for path in (root / directory).rglob("*")
        if path.is_file()
    ]
    assert len(sources) == 746, "Incomplete prepared C++/Python sources"
    assert digest(root, sources) == SOURCE_DIGEST, "Prepared source differs from dpkg-source"
    for name, expected in METADATA.items():
        actual = hashlib.sha256((root / "debian" / name).read_bytes()).hexdigest()
        assert actual == expected, "Debian metadata changed: " + name
    print("All 32 original Debian patches, 746 C++/Python source files and metadata match dpkg-source")


def main():
    from python.runfiles import runfiles

    parser = argparse.ArgumentParser()
    parser.add_argument("--source-marker", required=True)
    args = parser.parse_args()
    marker = runfiles.Create().Rlocation(args.source_marker)
    assert marker, "Missing declared source marker"
    # Keep the runfiles path: resolving its symlink would leave declared inputs.
    verify(Path(marker).parents[2])


if __name__ == "__main__":
    main()
