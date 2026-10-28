"""Reproduce the pinned compat-12 documentation selection from effective inputs."""
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import gzip
import json
from pathlib import Path
import re
import argparse


def debian_changelog(data, package):
    text = data.decode()
    starts = [m.start() for m in re.finditer(r'^net-snmp \(', text, re.M)]
    cutoff = datetime(2019, 7, 6, tzinfo=timezone.utc)
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(text)
        signature = re.search(r'^ -- .*?  (.+)$', text[start:end], re.M)
        try:
            date = parsedate_to_datetime(signature[1])
        except (TypeError, ValueError):
            return data
        if index >= 4 and date < cutoff:
            footer = ('# Older entries have been removed from this changelog.\n'
                      '# To read the complete changelog use `apt changelog ' + package + '`.\n')
            return (text[:start].rstrip() + '\n\n' + footer).encode()
    return data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-marker', required=True)
    parser.add_argument('--files', required=True, type=json.loads)
    parser.add_argument('--package', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    source = Path(args.source_marker).parent
    directory = Path(args.output) / 'usr/share/doc' / args.package
    directory.mkdir(parents=True)
    files = {name: (source / original).read_bytes() for name, original in args.files.items()}
    files['changelog'] = (source / 'ChangeLog').read_bytes()
    files['changelog.Debian'] = debian_changelog((source / 'debian/changelog').read_bytes(), args.package)
    for name, data in sorted(files.items()):
        if name != 'copyright' and (len(data) > 4096 or name.startswith(('changelog', 'NEWS'))):
            name += '.gz'
            data = gzip.compress(data, compresslevel=9, mtime=0)
        (directory / name).write_bytes(data)


if __name__ == '__main__':
    main()
