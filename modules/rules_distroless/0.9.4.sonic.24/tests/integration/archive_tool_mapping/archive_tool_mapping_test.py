"""Check layers produced by both branches of deb_postfix in an external caller."""

import sys
import tarfile


for archive_path, expected in zip(sys.argv[1:], ("./bin/probe", "./usr/bin/probe"), strict=True):
    with tarfile.open(archive_path, "r:gz") as archive:
        (member,) = [entry for entry in archive if entry.isfile()]
        assert member.name == expected, (member.name, expected)
        assert member.mode == 0o751, member.mode
        assert archive.extractfile(member).read() == b"archive tool mapping fixture\n"
