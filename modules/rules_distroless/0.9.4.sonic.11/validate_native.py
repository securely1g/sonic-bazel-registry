#!/usr/bin/env python3
"""Retain the locked-import source checks around registry-native validation."""
import argparse
import hashlib
import json
import platform
from pathlib import Path
import subprocess
import sys

ENTRY = Path(__file__).resolve().parent
ROOT = ENTRY.parents[2]


def source_inputs(entry):
    return {str(path.relative_to(entry)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(entry.rglob('*'))
            if path.is_file() and '__pycache__' not in path.parts}


def verify_native(architecture):
    machine = {'amd64': 'x86_64', 'arm64': 'aarch64'}[architecture]
    userspace = subprocess.check_output(['dpkg', '--print-architecture'], text=True).strip()
    if platform.system() != 'Linux' or platform.machine() != machine or userspace != architecture:
        raise ValueError('Requested architecture must match the native Linux host and Debian userspace')
    return {'system': platform.system(), 'machine': platform.machine(), 'userspace': userspace}


def regenerate_fixture(entry, artifacts):
    fixture = entry / 'tests/integration/apt.lock.json'
    regenerated = artifacts / 'regenerated-locked-import-fixture.json'
    subprocess.run([sys.executable, str(entry / 'tools/select_lock_fixture.py'),
                    '--input', str(fixture), '--output', str(regenerated)], check=True)
    if fixture.read_bytes() != regenerated.read_bytes():
        raise ValueError('Fixture regeneration differs from the reviewed lock')
    return hashlib.sha256(regenerated.read_bytes()).hexdigest()


def validate(entry, artifacts, architecture, command, source_head=None):
    native = verify_native(architecture)
    artifacts.mkdir(parents=True, exist_ok=True)
    inputs = source_inputs(entry)
    receipt = {'source_head': source_head, 'architecture': architecture, 'native': native,
               'recipe': str(entry.relative_to(ROOT)), 'source_inputs': inputs,
               'result': 'incomplete'}
    try:
        receipt['fixture_sha256'] = regenerate_fixture(entry, artifacts)
        receipt['fixture_regeneration'] = 'identical'
        subprocess.run(command, check=True)
        receipt['result'] = 'passed'
    finally:
        receipt['source_inputs_unchanged'] = source_inputs(entry) == inputs
        if not receipt['source_inputs_unchanged']:
            receipt['result'] = 'failed: recipe inputs changed'
        (artifacts / 'locked-import-validation.json').write_text(json.dumps(receipt, indent=2) + '\n')
        if not receipt['source_inputs_unchanged']:
            raise ValueError('Locked-import source inputs changed during native validation')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['run'])
    parser.add_argument('--module', required=True, choices=['rules_distroless'])
    parser.add_argument('--version', required=True, choices=['0.9.4.sonic.11'])
    parser.add_argument('--architecture', required=True, choices=['amd64', 'arm64'])
    parser.add_argument('--artifacts', required=True, type=Path)
    args, _ = parser.parse_known_args()
    validate(ENTRY, args.artifacts.resolve(), args.architecture,
             [sys.executable, str(ROOT / 'ci/registry_ci.py'), *sys.argv[1:]],
             source_head=subprocess.check_output(
                 ['git', '-c', f'safe.directory={ROOT}', 'rev-parse', 'HEAD'],
                 cwd=ROOT, text=True).strip())


if __name__ == '__main__':
    main()
