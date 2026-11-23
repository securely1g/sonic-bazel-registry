"""Check original dh_runit install effects against declared package members."""
import argparse
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--runit', type=Path, required=True)
parser.add_argument('--members', type=Path, required=True)
parser.add_argument('--marker', type=Path, required=True)
parser.add_argument('--logscript', type=Path, required=True)
parser.add_argument('--logscript-template', type=Path, required=True)
args = parser.parse_args()
members = set(json.loads(args.members.read_text()))
required = set()
for line in args.runit.read_text().splitlines():
    line = line.split('#', 1)[0].strip()
    if not line:
        continue
    source, options = line.split()
    values = options.split(',')
    name = next(value.partition('=')[2] for value in values if value.startswith('name='))
    if 'logscript' in values:
        required.update(['etc/sv/' + name + '/log/run', 'var/log/runit/' + name])
    required.update(['etc/sv/' + name + '/.meta/installed', 'usr/share/runit/meta/' + name + '/installed', 'etc/runit/runsvdir/default'])
missing = sorted(required - members)
if missing:
    parser.exit(1, 'Original dh_runit installation contract is blocked: missing '
                + ', '.join(missing)
                + '. The declared managed tools do not supply dh_runit to generate these assets.\n')
expected_logscript = args.logscript_template.read_text().replace('{{ logdir }}', '/var/log/runit/ssh')
if args.logscript.read_text() != expected_logscript:
    parser.exit(1, 'Original dh_runit logscript bytes differ from its source template.\n')
args.marker.write_text('Original dh_runit installation effects are present.\n')
