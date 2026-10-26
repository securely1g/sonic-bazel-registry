"""Generate original resource bytes from declared source/configuration inputs."""
import fnmatch
import gzip
import io
import json
from pathlib import Path, PurePosixPath
import posixpath
import re
import subprocess
import argparse
from python.runfiles import runfiles

parser = argparse.ArgumentParser()
parser.add_argument('--source-marker', required=True)
parser.add_argument('--manifest', required=True, type=json.loads)
parser.add_argument('--paths', required=True, type=json.loads)
parser.add_argument('--libdir', required=True)
parser.add_argument('--sedscript', required=True)
parser.add_argument('--configured-snmpconf', required=True)
parser.add_argument('--package', required=True)
parser.add_argument('--output', required=True)
args = parser.parse_args()
request = vars(args)
request['source_root'] = str(Path(args.source_marker).parent)
request['outputs'] = {args.package: args.output}
request['configured_files'] = {'local/snmpconf.in': args.configured_snmpconf}
request['perl'] = runfiles.Create().Rlocation('sonic_build_infra/tools/build_tools/perl_bookworm')
source = Path(request['source_root'])
manifest = request['manifest']
paths = request['paths']
paths['libdir'] = args.libdir
packages = {package: {} for package in request['outputs']}

def read(name):
    return (source / name).read_bytes()

def configured(name):
    return Path(request['configured_files'][name]).read_bytes()

# Normalize target-preprocessed resource substitutions.
substitutions = []
for line in Path(request['sedscript']).read_text(encoding='latin1').splitlines():
    if not line.startswith(('s/', 's#')):
        continue
    line = line.replace('REMOVEME', '')
    line = re.sub(r' */', '/', line)
    line = re.sub(r' *#', '#', line)
    line = re.sub(r'/ *', '/', line)
    line = line.replace('# g', '#g', 1)
    delimiter = line[1]
    parts = line.split(delimiter)
    if len(parts) != 4 or parts[0] != 's' or parts[-1] != 'g' or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', parts[1]):
        raise ValueError('unsupported original sedscript expression: ' + line)
    substitutions.append((parts[1], parts[2]))
for old, key in [('VERSIONINFO','VERSION'),('DATADIR','datadir'),('LIBDIR','libdir'),('BINDIR','bindir'),('PERSISTENT_DIRECTORY','PERSISTENT_DIRECTORY'),('SYSCONFDIR','sysconfdir')]:
    substitutions.append((old, paths[key]))

def sedscript(data):
    for old, new in substitutions:
        data = data.replace(old.encode('latin1'), new.encode('latin1'))
    return data

def add(package, name, data=None, mode=0o644, link=None):
    if package not in packages:
        return
    record = {'mode': mode, 'data': data} if link is None else {'mode': 0o777, 'link': link}
    if name in packages[package] and packages[package][name] != record:
        raise ValueError('conflicting original resource: ' + package + ':' + name)
    packages[package][name] = record


staged = {}
for group in ['MAN1','MAN1G','MAN3','MAN3G','MAN5G','MAN8G']:
    for name in manifest['manuals'][group]:
        if group in ['MAN1','MAN3']:
            data = read('man/' + name)
        elif name == 'default_store.3':
            lines = read('include/net-snmp/library/default_store.h').splitlines(keepends=True)
            selected, active = [], False
            for line in lines:
                if line.rstrip(b'\r\n') == b'     * begin storage definitions ': active = True
                elif line.rstrip(b'\r\n') == b'     * end storage definitions ': active = False
                elif active: selected.append(line)
            data = sedscript(read('man/default_store.3.top')) + b''.join(selected) + read('man/default_store.3.bot')
        elif name == 'mib2c.conf.5':
            result = subprocess.run([request['perl'], str(source / 'man/mib2c.extract.pl'), str(source / 'local/mib2c'), str(source / 'man/mib2c.conf.5.in')], check=True, capture_output=True)
            data = result.stdout
        else:
            data = sedscript(read('man/' + name + '.def'))
        staged['usr/share/man/man' + name.rsplit('.',1)[1] + '/' + name] = data

# API NAME sections independently validate the installed manual aliases.
derived_aliases = {}
for api in manifest['manuals']['MAN3_API']:
    body = staged['usr/share/man/man3/' + api].decode('utf8')
    names = body.split('.SH NAME\n',1)[1].split('.SH SYNOPSIS',1)[0]
    for line in names.splitlines():
        line = re.sub(r'.- .*', '', line).split(',',1)[0]
        if re.match(r'^.SH ', line): continue
        for name in line.split(): derived_aliases[name + '.3'] = api
if derived_aliases != manifest['aliases']:
    raise ValueError('original API alias NAME sections disagree with configured MANALIASES')
for alias, target in manifest['aliases'].items():
    staged['usr/share/man/man3/' + alias] = ('.so man3/' + target + '\n').encode()
for package, patterns in manifest['selectors'].items():
    for name, data in staged.items():
        if any(fnmatch.fnmatchcase(name, pattern) for pattern in patterns): add(package, name, data)
for package, records in manifest['man_extras'].items():
    for name, original in records.items(): add(package, name, read(original))

for name, specification in manifest['scripts'].items():
    data = configured(specification['source']) if specification.get('configure') else read(specification['source'])
    if specification['sedscript']: data = sedscript(data)
    text = data.decode('latin1')
    if specification['perl']: text = re.sub(r'^#!.*/perl.*$', '#!/usr/bin/perl', text, flags=re.MULTILINE)
    if name == 'mib2c':
        text = '\n'.join(line.replace('/usr/local/share/snmp', paths['datadir'] + '/snmp', 1).replace('/usr/local/etc/snmp', paths['SNMPCONFPATH'], 1) for line in text.split('\n'))
    if name == 'net-snmp-cert':
        text = '\n'.join(line.replace('/usr/local/share/snmp', paths['datadir'] + '/snmp', 1) for line in text.split('\n'))
    if name in ['snmpconf','traptoemail']:
        text = text.replace('/usr/local/share', paths['datadir']).replace('/usr/local/etc/snmp', paths['SNMPCONFPATH'] if name == 'snmpconf' else '')
        if name == 'snmpconf': text = text.replace('/var/net-snmp', paths['PERSISTENT_DIRECTORY'])
    add(specification['package'], specification['destination'], text.encode('latin1'), mode=0o755)
# Fixed Bookworm debhelper13.11.4 converts .so pages to links, then gzip -9n
# compresses manpages and updates the links to the compressed targets.
for package, records in packages.items():
    for name, record in list(records.items()):
        if not name.startswith('usr/share/man/') or 'data' not in record: continue
        data = record['data']
        first = data.splitlines()[0] if data else b''
        match = re.search(rb'\.so\s+(.*)', first) if 0 < len(data) <= 1024 else None
        if match:
            target = match[1].decode().strip()
            target = PurePosixPath(target).name if PurePosixPath(name).parent.name == str(PurePosixPath(target).parent) else '../' + target if '/' in target else target
            resolved = posixpath.normpath(posixpath.join(str(PurePosixPath(name).parent),target))
            if resolved in records: records[name] = {'mode': 0o777, 'link': target}
    for name, record in list(records.items()):
        if not name.startswith('usr/share/man/'): continue
        del records[name]
        if 'link' in record:
            record['link'] += '.gz'
        else:
            stream = io.BytesIO()
            with gzip.GzipFile(filename='', fileobj=stream, mode='wb', compresslevel=9, mtime=0) as output: output.write(record['data'])
            record['data'] = stream.getvalue()
        records[name + '.gz'] = record
    directory = Path(request['outputs'][package])
    directory.mkdir(parents=True, exist_ok=True)
    for name, record in sorted(records.items()):
        output = directory / name
        output.parent.mkdir(parents=True, exist_ok=True)
        # The BUILD's mtree metadata declares the installed relative links.
        # Emit only transformed regular files; sandbox symlinks are not payload.
        if 'link' not in record:
            output.write_bytes(record['data'])
            output.chmod(record['mode'])
