"""Execute the upstream Release CTest cases with declared relocated fixtures."""
import argparse
import errno
import fcntl
import json
import os
from pathlib import Path
import pty
import re
import shutil
import subprocess
import sys
import tempfile
import termios
import time
from python.runfiles import runfiles as runfiles_lib


def header_check(source):
    script = (source / 'compat/check_includes.sh').read_text()
    failures = []
    for kind, name in re.findall(r'^check_compat_(func|macro) (\w+)$', script, re.M):
        pattern = re.compile(r'([^A-Za-z0-9]|^)' + re.escape(name) + (r'\([^\n)]+\)' if kind == 'func' else r'([^A-Za-z0-9]|$)'), re.M)
        for directory in ['src', 'tools/lint', 'tools/re']:
            for path in (source / directory).rglob('*'):
                if path.suffix not in ('.c', '.h'):
                    continue
                text = path.read_text()
                if pattern.search(text) and '#include "compat.h"' not in text:
                    failures.append(str(path.relative_to(source)) + ': ' + name)
    if failures:
        print('Original compatibility include check failed:', *failures, sep='\n')
    return int(bool(failures))


def main():
    parser = argparse.ArgumentParser()
    for name in ['fixture', 'binary', 'plugin']:
        parser.add_argument('--' + name, nargs=2, action='append', default=[])
    args = parser.parse_args()
    resolver = runfiles_lib.Create()
    request = {
        'fixtures': dict(args.fixture), 'binaries': dict(args.binary), 'plugins': dict(args.plugin),
        'tclsh': str(Path(resolver.Rlocation('sonic_build_infra/tools/build_tools/tclsh')).absolute()),
    }
    # exec_test supplies absolute runfile paths for declared target artifacts.
    runfiles = Path('/')
    results = []
    with tempfile.TemporaryDirectory(prefix='libyang-upstream-', dir=os.environ.get('TEST_TMPDIR')) as temporary:
        root = Path(temporary)
        source = root / 'source'
        build = root / 'build'
        for logical, path in request['fixtures'].items():
            target = source / logical
            target.parent.mkdir(parents=True, exist_ok=True)
            target.symlink_to((runfiles / path).resolve())
        tests = build / 'tests'
        for directory in ['utests', 'CMakeFiles', 'plugins']:
            (tests / directory).mkdir(parents=True, exist_ok=True)
        binaries = {}
        for logical, path in request['binaries'].items():
            target = tests / logical
            if logical == 'utest_context':
                # test_searchdirs checks realpath(TESTS_BIN/utest_context).
                # Keep a regular executable at that path without copying bytes.
                target.hardlink_to((runfiles / path).resolve())
            else:
                target.symlink_to((runfiles / path).resolve())
            binaries[logical] = target
        for name, path in request['plugins'].items():
            (tests / 'plugins' / name).symlink_to((runfiles / path).resolve())
        environment = dict(os.environ, LIBYANG_TESTS_SRC=str(source / 'tests'), LIBYANG_TESTS_BIN=str(tests), MALLOC_CHECK_='3', LC_ALL='C')

        def execute(name, command, cwd=tests, env=environment, tcl=False):
            print('=== Original test:', name, '===', flush=True)
            started = time.monotonic()
            if name == 'yanglint_interactive':
                # The Expect suite requires a controlling terminal.
                master, slave = pty.openpty()
                def controlling_terminal():
                    os.setsid()
                    fcntl.ioctl(0, termios.TIOCSCTTY, 0)
                process = subprocess.Popen([str(item) for item in command], cwd=cwd, env=env, stdin=slave, stdout=slave, stderr=slave, preexec_fn=controlling_terminal)
                os.close(slave)
                chunks = []
                try:
                    while True:
                        try:
                            block = os.read(master, 65536)
                        except OSError as error:
                            if error.errno != errno.EIO:
                                raise
                            break
                        if not block:
                            break
                        chunks.append(block)
                finally:
                    os.close(master)
                completed = subprocess.CompletedProcess(command, process.wait(), b''.join(chunks).decode(errors='replace').replace('\r', ''))
            else:
                completed = subprocess.run([str(item) for item in command], cwd=cwd, env=env, stdout=subprocess.PIPE if tcl else None, stderr=subprocess.STDOUT if tcl else None, text=tcl)
            result = {'name': name, 'exit_code': completed.returncode, 'seconds': time.monotonic() - started}
            if tcl:
                print(completed.stdout, flush=True)
                summary = re.search(r'^all\.tcl:\s+Total\s+(\d+)\s+Passed\s+(\d+)\s+Skipped\s+(\d+)\s+Failed\s+(\d+)', completed.stdout, re.M)
                counts = dict(zip(['total', 'passed', 'skipped', 'failed'], map(int, summary.groups()))) if summary else {}
                result['test_counts'] = counts
                # Tcl's cleanup hook can return zero after child interpreter
                # failures. Actual original tests must execute to validate a port.
                result['contract_pass'] = bool(counts and counts['passed'] and counts['total'] == counts['passed'] + counts['skipped'] and not counts['failed'] and 'Test file error:' not in completed.stdout)
            results.append(result)

        results.append({'name': 'headers', 'exit_code': header_check(source)})
        for name, binary in binaries.items():
            if name.startswith('utest_'):
                execute(name, [binary])
        for name in ['lys_parse_mem', 'lyd_parse_mem_xml', 'lyd_parse_mem_json']:
            directory = tests / 'fuzz' / name
            shutil.copytree(source / 'tests/fuzz/corpus' / name, directory, copy_function=os.symlink)
            harness = directory / ('regress_fuzz_' + name)
            harness.symlink_to(binaries['regress_fuzz_' + name])
            execute('regress_fuzz_' + name, [binaries['fuzz_regression_test'], harness, '.'], cwd=directory)
        for tool in ['yanglint', 'yangre']:
            (build / tool).symlink_to(binaries[tool])
        tclsh = runfiles / request['tclsh']
        for name, directory, script in [
            ('yanglint_interactive', 'yanglint', 'interactive/all.tcl'),
            ('yanglint_non-interactive', 'yanglint', 'non-interactive/all.tcl'),
            ('yangre', 'yangre', 'all.tcl'),
        ]:
            test_source = source / 'tests' / directory
            # Original Tcl helpers support relative fixture paths. Keep echoed
            # commands independent of the sandbox's absolute path length;
            # upstream interactive tests set a fixed 720-column terminal.
            env = dict(environment, TESTS_DIR=os.path.relpath(test_source, build), YANG_MODULES_DIR=os.path.relpath(test_source / 'modules', build), YANGLINT=str(build), YANGRE=str(build))
            execute(name, [tclsh, test_source / script], cwd=build, env=env, tcl=True)
    output = Path(os.environ.get('TEST_UNDECLARED_OUTPUTS_DIR', tempfile.gettempdir())) / 'upstream-results.json'
    output.write_text(json.dumps(results, indent=2) + '\n')
    print(json.dumps(results, indent=2), flush=True)
    return int(any(result['exit_code'] or not result.get('contract_pass', True) for result in results))


if __name__ == '__main__':
    raise SystemExit(main())
