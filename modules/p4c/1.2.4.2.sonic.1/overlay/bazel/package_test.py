"""Exercise source-built P4C and verify its installed runtime/debug pair."""
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import struct
import zlib
import tarfile
import tempfile


def run(*args):
    return subprocess.check_output(args, text=True, stderr=subprocess.STDOUT)


def build_id(path):
    return re.search(r'Build ID: ([0-9a-f]+)', run('readelf', '-n', str(path))).group(1)


with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    runtime, debug, compiler, commands, cache = map(Path, sys.argv[1:])
    compilation = json.loads(commands.read_text())
    assert any("/build/_deps/protobuf-src/" in item["file"] for item in compilation)
    assert any("/frontends/" in item["file"] for item in compilation)
    assert all("gcc-14.2.0-linux" in item["command"] for item in compilation)
    configuration = cache.read_text()
    assert "ENABLE_BMV2:BOOL=ON" in configuration
    assert "CMAKE_INSTALL_PREFIX:PATH=/usr" in configuration
    frontend_commands = [shlex.split(item["command"]) for item in compilation if "/frontends/" in item["file"]]
    assert all('-DCONFIG_PREFIX="/usr"' in command for command in frontend_commands)
    assert all('-DCONFIG_PKGDATADIR="/usr/share/p4c"' in command for command in frontend_commands)
    for line in configuration.splitlines():
        if re.match(r"Boost_.*(?:LIBRARY|INCLUDE_DIR|LIBRARY_DIR).*:(?:PATH|FILEPATH)=", line):
            assert "/p4c.ext_build_deps/" in line, line
    assert re.search(r"^CCACHE_PROGRAM:[^=]+=OFF$", configuration, re.MULTILINE)
    assert "CMAKE_DISABLE_FIND_PACKAGE_nlohmann_json:BOOL=ON" in configuration
    testgen_commands = [item["command"] for item in compilation if "/backends/p4tools/modules/testgen/" in item["file"]]
    if "ENABLE_TEST_TOOLS:BOOL=ON" in configuration:
        assert testgen_commands
        assert all("/build/_deps/inja-src/third_party/include" in command for command in testgen_commands)
    assert all(not re.search(r"(?:^|\s)(?:\S*/)?ccache(?:\s|$)", item["command"]) for item in compilation)
    for archive, destination in [(runtime, root / 'runtime'), (debug, root / 'debug')]:
        with tarfile.open(archive) as tar:
            tar.extractall(destination, filter='data')
    binary = root / 'runtime/usr/bin/p4c-bm2-ss'
    identifier = build_id(binary)
    symbols = root / 'debug/usr/lib/debug/.build-id' / identifier[:2] / (identifier[2:] + '.debug')
    assert build_id(symbols) == identifier
    link = root / 'debuglink'
    run('objcopy', '--dump-section=.gnu_debuglink=' + str(link), str(binary))
    data = link.read_bytes()
    assert data.split(b'\0', 1)[0].decode() == symbols.name
    assert struct.unpack('<I', data[-4:])[0] == zlib.crc32(symbols.read_bytes())
    assert '.debug_info' not in run('readelf', '-SW', str(binary))
    assert '.debug_info' in run('readelf', '-SW', str(symbols))
    assert 'core.p4' in '\n'.join(str(p) for p in (root / 'runtime/usr/share/p4c/p4include').rglob('*'))
    line = run('gdb', '--batch', '--nx', '-ex', 'set debuginfod enabled off', '-ex', 'set debug-file-directory ' + str(root / 'debug/usr/lib/debug'), '-ex', 'file ' + str(binary), '-ex', 'info line main')
    assert re.search(r'Line [0-9]+ of .*main.cpp', line), line
    version = run(str(compiler.resolve()), '--version')
    assert '1.2.4.2' in version, version
    # Reproduce a nested Python caller whose RUNFILES_DIR belongs to itself,
    # while FilesToRun supplies the compiler's own complete adjacent tree.
    nested = root / 'nested-compiler'
    shutil.copy2(compiler.resolve(), nested)
    Path(str(nested) + '.runfiles').symlink_to(Path(os.environ['RUNFILES_DIR']).resolve(), target_is_directory=True)
    unrelated = root / 'caller.runfiles'
    unrelated.mkdir()
    nested_version = subprocess.check_output([str(nested), '--version'], text=True, stderr=subprocess.STDOUT,
                                             env=dict(os.environ, RUNFILES_DIR=str(unrelated)))
    assert '1.2.4.2' in nested_version, nested_version
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
    assert isinstance(json.loads((root / 'p4info.json').read_text()), dict)
    assert isinstance(json.loads((root / 'ir.json').read_text()), dict)
    print(json.dumps({'version':version.strip(), 'runtime_build_id':identifier, 'compiled_bmv2':True}))
