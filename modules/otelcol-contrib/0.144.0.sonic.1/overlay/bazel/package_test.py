"""Validate installed OTEL payloads and the original startup/golden contracts.

All production artifacts, original test inputs and the upstream golden executable
are declared arguments. This test never downloads dependencies or builds code.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import socket
import struct
import subprocess
import tarfile
import tempfile
import time
import zlib

EPOCH = 1672560000
BINARY = 'usr/bin/otelcol-contrib'
RUNTIME_FILES = {
    'etc/otelcol-contrib/config.yaml',
    'etc/otelcol-contrib/otelcol-contrib.conf',
    'lib/systemd/system/otelcol-contrib.service',
    'usr/share/doc/otelcol-contrib/copyright',
}
SOURCE_FILES = {'components.go', 'main.go', 'main_others.go', 'manifest.yaml', 'go.mod', 'go.sum'}
GOLDEN_FLAGS = [
    '--expected', '/var/data/expected.yaml',
    '--otlp-http-endpoint', '0.0.0.0:4318', '--otlp-endpoint', '0.0.0.0:4317',
    '--ignore-timestamp', '--ignore-start-timestamp', '--timeout', '2m',
    '--ignore-resource-attribute-value', 'service.instance.id',
    '--ignore-metric-attribute-value', 'service.instance.id',
    '--ignore-resource-attribute-value', 'service.version',
    '--ignore-resource-attribute-value', 'service.name',
    '--ignore-metric-attribute-value', 'service.version',
    '--ignore-metric-attribute-value', 'service.name',
    '--ignore-resource-metrics-order', '--ignore-scope-metrics-order',
    '--ignore-metrics-order', '--ignore-metrics-data-points-order',
    '--ignore-metric-values', '--ignore-data-points-attributes-order', '--ignore-scope-version',
]


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def command(argv, env, *, check=True, timeout=45):
    result = subprocess.run([str(a) for a in argv], env=env, capture_output=True, timeout=timeout)
    if check and result.returncode:
        raise AssertionError(repr(argv) + '\n' + result.stdout.decode(errors='replace') + result.stderr.decode(errors='replace'))
    return result


def mapping(values, expected):
    result = {}
    for value in values:
        name, path = value.split('=', 1)
        assert name not in result, 'Duplicate expected input: ' + name
        result[name] = Path(path).resolve(strict=True)
    assert set(result) == expected, set(result) ^ expected
    return result


def normalize_components(output):
    """Sort only the release command's unsorted ProviderModules map records."""
    marker = b'\nproviders:\n'
    assert output.count(marker) == 1, 'Expected one final providers section'
    prefix, providers = output.split(marker)
    records = list(re.finditer(rb'    - scheme: ([a-z][a-z0-9]*)\n      module: [^\r\n]+\n', providers))
    assert records and b''.join(record.group() for record in records) == providers, 'Provider report format changed'
    assert len({record.group(1) for record in records}) == len(records), 'Duplicate provider scheme'
    return prefix + marker + b''.join(record.group() for record in sorted(records, key=lambda record: record.group(1)))


def unpack(archive, destination, expected, directory_mtimes=None):
    """Reject duplicate paths, undeclared files, links and noncanonical metadata."""
    with tarfile.open(archive) as source:
        members = {}
        allowed_directories = {parent.as_posix() for name in expected for parent in PurePosixPath(name).parents}
        for member in source:
            name = member.name.removeprefix('./').rstrip('/') or '.'
            assert name and not name.startswith('/') and '..' not in PurePosixPath(name).parts, name
            assert name not in members, 'Duplicate archive path: ' + name
            members[name] = member
            assert member.isdir() or member.isfile(), 'Unexpected archive link/device: ' + name
            if member.isdir():
                assert name in allowed_directories and member.mode == 0o755, (name, oct(member.mode))
            mtime = (directory_mtimes or {}).get(name, EPOCH) if member.isdir() else EPOCH
            assert (member.uid, member.gid, member.mtime) == (0, 0, mtime), (name, member.uid, member.gid, member.mtime)
        files = {name: member for name, member in members.items() if member.isfile()}
        assert set(files) == set(expected), set(files) ^ set(expected)
        for name, mode in expected.items():
            assert files[name].mode == mode, (name, oct(files[name].mode), oct(mode))
        source.extractall(destination, filter='data')
    return files


def stop(process):
    if process is not None and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)


def free_port():
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        return listener.getsockname()[1]


def require_metrics_port():
    # Keep the original expected.yaml's server.port=8888 unchanged. Tests must
    # run serially in their native CI worker; a conflict fails before startup.
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 8888))


def original_golden_flags(compose):
    text = compose.read_text()
    assert text.count('    command: >-\n') == 1, 'Upstream golden command changed'
    block = text.split('    command: >-\n', 1)[1]
    flags = shlex.split('\n'.join(line.strip() for line in block.splitlines() if line.strip().startswith('--')))
    assert flags == GOLDEN_FLAGS, 'Review original golden flags instead of silently dropping or weakening one'
    return flags


def startup_and_golden(args, binary, root, env):
    require_metrics_port()
    port = free_port()
    original = args.default_config.read_text()
    assert original.count('0.0.0.0:4317') == 2 and original.count('processors: []') == 1
    default = root / 'default-config.yaml'
    default.write_text(original.replace('0.0.0.0:4317', '127.0.0.1:' + str(port)))
    command([binary, 'validate', '--config', default], env)
    invalid = root / 'invalid.yaml'
    invalid.write_text(default.read_text().replace('processors: []', 'processors: [bazel_missing]') + '\nprocessors:\n  bazel_missing: {}\n')
    rejected = command([binary, 'validate', '--config', invalid], env, check=False)
    assert rejected.returncode and b'bazel_missing' in rejected.stdout + rejected.stderr, 'Unknown processor was not rejected'
    startup_log = root / 'startup.log'
    process = None
    try:
        with startup_log.open('wb') as output:
            process = subprocess.Popen([str(binary), '--config', str(default)], env=env, stdout=output, stderr=subprocess.STDOUT)
            time.sleep(10)  # The original release CI checks readiness after 10 seconds.
            assert process.poll() is None and b'Everything is ready.' in startup_log.read_bytes(), startup_log.read_text(errors='replace')
    finally:
        stop(process)

    require_metrics_port()
    grpc_port, http_port = free_port(), free_port()
    while http_port == grpc_port:
        http_port = free_port()
    golden_config = root / 'golden-config.yaml'
    text = args.golden_config.read_text()
    assert text.count('0.0.0.0:8888') == 1 and text.count('http://golden:4317') == 1
    golden_config.write_text(text.replace('0.0.0.0:8888', '127.0.0.1:8888').replace('http://golden:4317', 'http://127.0.0.1:' + str(grpc_port)))
    command([binary, 'validate', '--config', golden_config], env)
    flags = original_golden_flags(args.golden_compose)
    replacements = {'/var/data/expected.yaml': str(args.golden_expected),
                    '0.0.0.0:4317': '127.0.0.1:' + str(grpc_port),
                    '0.0.0.0:4318': '127.0.0.1:' + str(http_port)}
    arguments = [replacements.get(value, value) for value in flags]
    expected_hash = digest(args.golden_expected)
    golden_log, collector_log = root / 'golden.log', root / 'golden-collector.log'
    golden = collector = None
    try:
        with golden_log.open('wb') as receiver_output, collector_log.open('wb') as collector_output:
            golden = subprocess.Popen([str(args.golden), *arguments], env=env, stdout=receiver_output, stderr=subprocess.STDOUT)
            # Start the exporter only when both original OTLP listeners accept
            # connections. The golden tool retains its original two-minute limit.
            deadline = time.monotonic() + 15
            ready = False
            while time.monotonic() < deadline:
                assert golden.poll() is None, golden_log.read_text(errors='replace')
                try:
                    with socket.create_connection(('127.0.0.1', grpc_port), timeout=.2), socket.create_connection(('127.0.0.1', http_port), timeout=.2):
                        ready = True
                        break
                except OSError:
                    time.sleep(.1)
            assert ready, 'Original golden OTLP listeners did not start: ' + golden_log.read_text(errors='replace')
            collector = subprocess.Popen([str(binary), '--config', str(golden_config)], env=env, stdout=collector_output, stderr=subprocess.STDOUT)
            deadline = time.monotonic() + 125
            while golden.poll() is None and time.monotonic() < deadline:
                assert collector.poll() is None, collector_log.read_text(errors='replace')
                time.sleep(.2)
            assert golden.poll() == 0, golden_log.read_text(errors='replace') + '\n' + collector_log.read_text(errors='replace')
            assert collector.poll() is None and b'Everything is ready.' in collector_log.read_bytes(), collector_log.read_text(errors='replace')
    finally:
        stop(collector)
        stop(golden)
    assert digest(args.golden_expected) == expected_hash, 'Golden expected data changed'
    return {'startup_ready_after_seconds': 10, 'invalid_processor_rejected': True,
            'golden_expected_sha256': expected_hash, 'original_golden_options': flags,
            'adaptation': 'Loopback/private OTLP endpoints only; telemetry port8888 and original expected metrics unchanged'}


def inspect_symbols(args, binary, debug, root, env):
    def elf(path, *options):
        return command([args.readelf, *options, path], env).stdout.decode()
    for path in (binary, args.binary):
        assert 'Advanced Micro Devices X86-64' in elf(path, '-h')
        assert 'INTERP' not in elf(path, '-lW') and '(NEEDED)' not in elf(path, '-dW'), 'Collector must be static pure Go'
    assert '.debug_info' not in elf(binary, '-SW') and '.debug_info' in elf(args.binary, '-SW')
    build_id = re.search(r'Build ID: ([0-9a-f]+)', elf(binary, '-n')).group(1)
    assert set(build_id) != {'0'} and build_id in elf(args.binary, '-n')
    relative = 'usr/lib/debug/.build-id/' + build_id[:2] + '/' + build_id[2:] + '.debug'
    # The selected shared debug rule normalizes symbol files to mode0644.
    # Its four synthesized parents use the fixed default.awk epoch; explicit
    # .build-id entries retain the generated mtree epoch used for other payloads.
    unpack(args.debug, debug, {relative: 0o644},
           {name: 946699200 for name in ('.', 'usr', 'usr/lib', 'usr/lib/debug')})
    symbols = debug / relative
    assert '.debug_info' in elf(symbols, '-SW') and build_id in elf(symbols, '-n')
    section = root / 'debuglink.bin'
    command([args.objcopy, '--dump-section', '.gnu_debuglink=' + str(section), binary, root / 'inspection-copy'], env)
    link = section.read_bytes()
    assert link.split(b'\0', 1)[0].decode() == symbols.name
    crc = 0
    with symbols.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            crc = zlib.crc32(chunk, crc)
    assert struct.unpack('<I', link[-4:])[0] == crc & 0xffffffff, 'GNU debuglink CRC differs'
    empty = root / 'empty-debug';empty.mkdir()
    checks = []
    for directory, present in ((debug / 'usr/lib/debug', True), (empty, False)):
        result = command([args.gdb, '--nx', '--nh', '--batch', '-iex', 'set auto-load off',
            '-iex', 'set debuginfod enabled off', '-ex', 'set debug-file-directory ' + str(directory),
            '-ex', 'file ' + str(binary), '-ex', "info line 'main.main'", '-ex', "ptype 'main.main'"], env, check=False)
        output = (result.stdout + result.stderr).decode(errors='replace')
        assert bool(re.search(r'Line \d+ of "[^"\n]+\.go"', output)) == present, output
        if present:
            assert result.returncode == 0 and 'type =' in output, output
        (root / ('gdb-present.log' if present else 'gdb-absent.log')).write_text(output)
        checks.append({'symbols_present': present, 'source_line_available': present})
    return {'gnu_build_id': build_id, 'debuglink_crc_verified': True, 'gdb': checks}


def validate_buildinfo(observed, baseline):
    """Compare the linked executable's standard Go metadata with the release."""
    assert baseline['GoVersion'] == 'go1.25.6' and len(baseline['Deps']) == 1007
    assert observed['GoVersion'] == baseline['GoVersion'], observed['GoVersion']
    assert observed['Path'] == baseline['Path'], observed['Path']

    def modules(info):
        result = {}
        for module in info['Deps']:
            name = module['Path']
            assert name not in result and not module.get('Replace'), module
            assert module['Sum'].startswith('h1:'), module
            result[name] = (module['Version'], module['Sum'])
        return result

    expected, actual = modules(baseline), modules(observed)
    assert actual == expected, {
        'missing': sorted(set(expected) - set(actual)),
        'extra': sorted(set(actual) - set(expected)),
        'different': {name: {'expected': expected[name], 'actual': actual[name]}
                      for name in sorted(set(expected) & set(actual)) if expected[name] != actual[name]},
    }
    settings = {item['Key']: item['Value'] for item in observed['Settings']}
    assert len(settings) == len(observed['Settings']), 'Duplicate Go build setting'
    required = {'-buildmode': 'exe', '-compiler': 'gc', '-trimpath': 'true',
                'CGO_ENABLED': '0', 'GOARCH': 'amd64', 'GOOS': 'linux', 'GOAMD64': 'v1'}
    release_settings = {item['Key']: item['Value'] for item in baseline['Settings']}
    for name, value in required.items():
        assert release_settings[name] == value
        assert settings.get(name) == value, (name, settings.get(name), value)
    for name in ('-tags', '-race', '-msan', '-asan', 'GOEXPERIMENT'):
        assert settings.get(name, '') == release_settings.get(name, ''), (name, settings.get(name))
    return {'go_version': observed['GoVersion'], 'linked_module_count': len(actual),
            'release_versions_and_checksums_match': True, 'settings': required}


def inspect_buildinfo(args, binary, artifact_root, env):
    baseline = json.loads(args.baseline_buildinfo.read_text())
    observed = json.loads(command([args.buildinfo, binary], env).stdout)
    (artifact_root / 'installed-buildinfo.json').write_text(json.dumps(observed, indent=2) + '\n')
    report = validate_buildinfo(observed, baseline)
    original = json.loads(command([args.buildinfo, args.binary], env).stdout)
    assert observed == original, 'Runtime stripping changed embedded Go build metadata'
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('runtime', 'debug', 'sources', 'binary', 'metadata', 'readelf', 'objcopy', 'gdb', 'golden',
                 'baseline-version', 'baseline-components', 'buildinfo', 'baseline-buildinfo', 'default-config', 'golden-config', 'golden-compose', 'golden-expected'):
        parser.add_argument('--' + name, type=lambda value: Path(value).resolve(strict=True), required=True)
    parser.add_argument('--runtime-file', action='append', required=True)
    parser.add_argument('--source-file', action='append', required=True)
    args = parser.parse_args()
    runtime_files = mapping(args.runtime_file, RUNTIME_FILES)
    source_files = mapping(args.source_file, SOURCE_FILES)
    env = {key: value for key, value in os.environ.items() if key not in ('LD_LIBRARY_PATH', 'LD_PRELOAD', 'LD_AUDIT', 'GODEBUG')}
    env.update(LC_ALL='C', TZ='UTC', DEBUGINFOD_URLS='')
    # Retain diagnostic logs on failure in the standard Bazel artifact directory.
    artifact_root = Path(os.environ['TEST_UNDECLARED_OUTPUTS_DIR']) if os.environ.get('TEST_UNDECLARED_OUTPUTS_DIR') else Path(tempfile.mkdtemp(prefix='otel-test-evidence-'))
    artifact_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='otel-installed-') as temporary:
        root = Path(temporary);payload=root/'payload';debug=root/'debug';sources=root/'sources'
        for directory in (payload, debug, sources):directory.mkdir()
        try:
            unpack(args.runtime, payload, {BINARY: 0o755, **{name: 0o644 for name in RUNTIME_FILES}})
            for name, original in runtime_files.items():assert digest(payload/name) == digest(original), name
            elf_files = []
            for path in payload.rglob('*'):
                if path.is_file():
                    with path.open('rb') as stream:
                        if stream.read(4) == b'\x7fELF':elf_files.append(path.relative_to(payload).as_posix())
            assert elf_files == [BINARY], elf_files
            expected_sources = {'usr/src/debug/otelcol-contrib/' + name: 0o644 for name in SOURCE_FILES}
            unpack(args.sources, sources, expected_sources)
            for name, original in source_files.items():assert digest(sources/'usr/src/debug/otelcol-contrib'/name) == digest(original), name
            metadata = json.loads(args.metadata.read_text())
            assert metadata['architecture'] == 'amd64' and set(metadata['packages']) == {'otelcol-contrib'}
            assert metadata['packages']['otelcol-contrib']['control_fields']['Version'] == '0.144.0'
            binary = payload / BINARY
            for argument, baseline in (('--version', args.baseline_version), ('components', args.baseline_components)):
                observed = command([binary, argument], env)
                expected = baseline.read_bytes()
                actual = observed.stdout
                if argument == 'components':
                    actual, expected = normalize_components(actual), normalize_components(expected)
                assert actual == expected, 'Official release stdout differs: ' + argument
            command([binary, 'validate', '--config', payload / 'etc/otelcol-contrib/config.yaml'], env)
            buildinfo = inspect_buildinfo(args, binary, artifact_root, env)
            symbols = inspect_symbols(args, binary, debug, root, env)
            service = startup_and_golden(args, binary, root, env)
            report = {'status':'passed', 'runtime_sha256':digest(args.runtime), 'debug_sha256':digest(args.debug),
                      'source_sha256':digest(args.sources), 'installed_sha256':digest(binary), 'symbols':symbols,
                      'service':service, 'buildinfo':buildinfo, 'source_scope':'Generated entrypoints, manifest and canonical locks only'}
            (artifact_root/'installed-otel.json').write_text(json.dumps(report,indent=2)+'\n')
            print(json.dumps(report,sort_keys=True))
        finally:
            for path in root.glob('*.log'):
                (artifact_root/path.name).write_bytes(path.read_bytes())


if __name__ == '__main__':
    main()
