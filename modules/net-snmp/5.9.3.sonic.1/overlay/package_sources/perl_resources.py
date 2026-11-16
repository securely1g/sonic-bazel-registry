"""Generate PM AutoSplit resources and POD pages with the declared target-era Perl."""
from email.utils import parsedate_to_datetime
import gzip
import json
import os
from pathlib import Path
import re
import subprocess
import argparse
from python.runfiles import runfiles
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument('--source-marker', required=True)
parser.add_argument('--mapping', required=True, type=json.loads)
parser.add_argument('--vendorarch', required=True)
parser.add_argument('--output', required=True)
args = parser.parse_args()
request = vars(args)
request['source_root'] = str(Path(args.source_marker).parent)
request['mapping']['vendorarch'] = args.vendorarch
request['perl'] = runfiles.Create().Rlocation('sonic_build_infra/tools/build_tools/perl_bookworm')
output_root = Path(args.output)
output_root.mkdir(parents=True, exist_ok=True)
source = Path(request['source_root'])
mapping = request['mapping']
perl = str(Path(request['perl']).absolute())
first_signature = re.search(rb'^ -- .*?  (.+)$', (source / 'debian/changelog').read_bytes(), re.M)
environment = os.environ | {'SOURCE_DATE_EPOCH': str(int(parsedate_to_datetime(first_signature[1].decode()).timestamp()))}
with tempfile.TemporaryDirectory() as temporary:
    staging = Path(temporary)
    for entry in mapping['pm_to_blib']:
        directory = staging / 'perl' / entry['module']
        directory.mkdir(parents=True, exist_ok=True)
        (directory / entry['source']).symlink_to((source / entry['input']).absolute())
        subprocess.run([perl, '-MExtUtils::Install', '-e', 'my $auto = shift @ARGV; ExtUtils::Install::pm_to_blib({@ARGV}, $auto, q[], 0755);', '--', entry['INST_LIB'] + '/auto', entry['source'], entry['destination']], cwd=directory, env=environment, check=True)
    for file in sorted((staging / 'perl/blib/lib').rglob('*')):
        if not file.is_file():
            continue
        output = output_root / mapping['vendorarch'].lstrip('/') / file.relative_to(staging / 'perl/blib/lib')
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(file.read_bytes())
    for entry in mapping['pods']:
        output = staging / 'perl' / entry['output']
        output.parent.mkdir(parents=True, exist_ok=True)
        directory = staging / 'perl' / entry['module']
        relative_output = os.path.relpath(output, directory)
        subprocess.run([perl, '-MExtUtils::Command::MM', '-e', 'pod2man', '--', *entry['arguments'], entry['source'], relative_output], cwd=directory, env=environment, check=True)
        data = gzip.compress(output.read_bytes(), compresslevel=9, mtime=0)
        installed = output_root / (entry['installed'].lstrip('/') + '.gz')
        installed.parent.mkdir(parents=True, exist_ok=True)
        installed.write_bytes(data)
