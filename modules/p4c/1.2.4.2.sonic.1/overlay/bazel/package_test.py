"""Exercise source-built P4C and verify its installed runtime/debug pair."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import tempfile


def run(*args):
    return subprocess.check_output(args, text=True, stderr=subprocess.STDOUT)


def build_id(path):
    return re.search(r'Build ID: ([0-9a-f]+)', run('readelf', '-n', str(path))).group(1)


with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    runtime, debug, compiler = map(Path, sys.argv[1:])
    for archive, destination in [(runtime, root / 'runtime'), (debug, root / 'debug')]:
        with tarfile.open(archive) as tar:
            tar.extractall(destination, filter='data')
    binary = root / 'runtime/usr/bin/p4c-bm2-ss'
    identifier = build_id(binary)
    symbols = root / 'debug/usr/lib/debug/.build-id' / identifier[:2] / (identifier[2:] + '.debug')
    assert build_id(symbols) == identifier
    assert '.debug_info' not in run('readelf', '-SW', str(binary))
    assert '.debug_info' in run('readelf', '-SW', str(symbols))
    assert 'core.p4' in '\n'.join(str(p) for p in (root / 'runtime/usr/share/p4c/p4include').rglob('*'))
    line = run('gdb', '--batch', '--nx', '-ex', 'set debuginfod enabled off', '-ex', 'set debug-file-directory ' + str(root / 'debug/usr/lib/debug'), '-ex', 'file ' + str(binary), '-ex', 'info line main')
    assert re.search(r'Line [0-9]+ of .*main.cpp', line), line
    version = run(str(compiler.resolve()), '--version')
    assert '1.2.4.2' in version, version
    source = root / 'smoke.p4'
    source.write_text('''#include <core.p4>
#include <v1model.p4>
struct H { } struct M { }
parser P(packet_in p, out H h, inout M m, inout standard_metadata_t sm) { state start { transition accept; } }
control V(inout H h, inout M m) { apply {} }
control I(inout H h, inout M m, inout standard_metadata_t sm) { apply { sm.egress_spec = 1; } }
control E(inout H h, inout M m, inout standard_metadata_t sm) { apply {} }
control C(inout H h, inout M m) { apply {} }
control D(packet_out p, in H h) { apply {} }
V1Switch(P(), V(), I(), E(), C(), D()) main;
''')
    output = root / 'smoke.json'
    run(str(compiler.resolve()), str(source), '-o', str(output), '--toJSON', str(root / 'ir.json'), '--p4runtime-files', str(root / 'p4info.json'))
    payload = json.loads(output.read_text())
    assert payload['program']
    assert json.loads((root / 'p4info.json').read_text())
    assert json.loads((root / 'ir.json').read_text())
    print(json.dumps({'version':version.strip(), 'runtime_build_id':identifier, 'compiled_bmv2':True}))
