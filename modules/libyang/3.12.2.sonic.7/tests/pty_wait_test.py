#!/usr/bin/python3 -IS
"""Exercise the exact source execute() bodies with real controlling terminals.

This is an isolated regression, not an upstream-suite or module acceptance run.
No source function, subprocess result, terminal operation, or wait is mocked.
"""
import argparse
import ast
import contextlib
import errno
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path
import pty
import re
import signal
import subprocess
import sys
import termios
import time


ORIGINAL_SHA = '9531f7dd2f3d05038143e5e63672da143196d9679cd979c454a1fb1c5dfc1918'
CANDIDATE_SHA = '19f9ce5c1b2e5a959816fb4b111185391ecd7ab659a8b7fc71c29576b8962944'
CHILD = r'''
import os, signal, sys, time
code, passed, close_early = map(int, sys.argv[1:])
if close_early:
    assert os.getsid(0) == os.getpid()
    assert os.getpgrp() == os.getpid()
    terminal = os.open('/dev/tty', os.O_RDWR)
    os.close(terminal)
    signal.signal(signal.SIGHUP, signal.SIG_DFL)
summary = 'all.tcl: Total 1 Passed %d Skipped 0 Failed %d\n' % (passed, 1 - passed)
os.write(1, summary.encode('ascii'))
if close_early:
    for descriptor in (0, 1, 2):
        os.close(descriptor)
    # Real PTY EOF now precedes a deliberate, normal process exit. Closing the
    # master during this window sends SIGHUP to this controlling session.
    time.sleep(0.5)
raise SystemExit(code)
'''


def children():
    path = Path('/proc') / str(os.getpid()) / 'task' / str(os.getpid()) / 'children'
    return {int(value) for value in path.read_text().split()}


def timeout(signum, frame):
    raise TimeoutError('Focused execute() case exceeded eight seconds')


def load_execute(path, expected_hash, work):
    raw = path.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    assert actual == expected_hash, (path, actual, expected_hash)
    tree = ast.parse(raw, filename=str(path))
    functions = [node for node in ast.walk(tree)
                 if isinstance(node, ast.FunctionDef) and node.name == 'execute']
    assert len(functions) == 1
    function = functions[0]
    results = []
    environment = {'PATH': '/usr/bin:/bin', 'HOME': str(work), 'LC_ALL': 'C'}
    namespace = dict(errno=errno, fcntl=fcntl, os=os, pty=pty, re=re,
                     subprocess=subprocess, termios=termios, time=time,
                     tests=work, environment=environment, results=results)
    # Compile the original AST node intact; only the enclosing fixture's
    # globals/default values are supplied, without importing its Bazel runfiles.
    module = ast.Module(body=[function], type_ignores=[])
    exec(compile(module, str(path), 'exec'), namespace)
    return namespace['execute'], results, {
        'path': str(path), 'sha256': actual,
        'execute_ast_sha256': hashlib.sha256(ast.dump(function).encode()).hexdigest(),
        'execute_source': ast.get_source_segment(raw.decode(), function),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--original', type=Path, default=Path(__file__).resolve().parents[2] / '3.12.2.sonic.6/overlay/upstream_tests.py')
    parser.add_argument('--candidate', type=Path, default=Path(__file__).resolve().parents[1] / 'overlay/upstream_tests.py')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.output.resolve()
    root.mkdir(mode=0o700, parents=True, exist_ok=False)
    child = root / 'terminal-child.py'
    child.write_text(CHILD)
    signal.signal(signal.SIGALRM, timeout)
    report = {'scope': 'Real PTY regression only; no upstream/module acceptance',
              'python': sys.executable, 'child_sha256': hashlib.sha256(CHILD.encode()).hexdigest(),
              'sources': {}, 'cases': [], 'passed': False}
    try:
        for version, path, digest in [('original', args.original, ORIGINAL_SHA),
                                      ('candidate', args.candidate, CANDIDATE_SHA)]:
            execute, results, source = load_execute(path.resolve(), digest, root)
            report['sources'][version] = source
            for label, code, passed, interactive in [
                    ('normal_exit', 0, 1, True),
                    ('nonzero_exit', 23, 1, True),
                    ('failed_summary', 0, 0, True),
                    ('noninteractive_control', 23, 1, False)]:
                before = children()
                output = io.StringIO()
                forced = []
                started = time.monotonic()
                try:
                    signal.setitimer(signal.ITIMER_REAL, 8)
                    with contextlib.redirect_stdout(output):
                        execute('yanglint_interactive' if interactive else 'yanglint_non-interactive',
                                [sys.executable, '-I', '-S', str(child), str(code), str(passed),
                                 str(int(interactive))], tcl=True)
                finally:
                    signal.setitimer(signal.ITIMER_REAL, 0)
                    # Only direct children of this otherwise child-free driver.
                    # Each fixture child either has its own session or has not
                    # yet executed the source's setsid; never signal our group.
                    for pid in children() - before:
                        try:
                            if os.getpgid(pid) == pid:
                                os.killpg(pid, signal.SIGKILL)
                            else:
                                os.kill(pid, signal.SIGKILL)
                            forced.append(pid)
                        except ProcessLookupError:
                            pass
                        try:
                            os.waitpid(pid, 0)
                        except ChildProcessError:
                            pass
                text = output.getvalue()
                (root / (version + '-' + label + '.log')).write_text(text)
                result = results[-1]
                expected = -signal.SIGHUP if version == 'original' and interactive else code
                record = {'source': version, 'case': label, 'expected_exit_code': expected,
                          'result': result, 'forced_cleanup': forced,
                          'seconds': time.monotonic() - started,
                          'stdout_sha256': hashlib.sha256(text.encode()).hexdigest()}
                report['cases'].append(record)
                assert not forced, record
                assert result['exit_code'] == expected, record
                assert result['test_counts'] == {'total': 1, 'passed': passed,
                                                 'skipped': 0, 'failed': 1 - passed}, record
                assert result['contract_pass'] is bool(passed), record
                accepted = result['exit_code'] == 0 and result['contract_pass']
                assert accepted == (version == 'candidate' and label == 'normal_exit'), record
        report['passed'] = True
    finally:
        (root / 'proof.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'passed': report['passed'], 'cases': len(report['cases']),
                      'proof': str(root / 'proof.json')}))


if __name__ == '__main__':
    main()
