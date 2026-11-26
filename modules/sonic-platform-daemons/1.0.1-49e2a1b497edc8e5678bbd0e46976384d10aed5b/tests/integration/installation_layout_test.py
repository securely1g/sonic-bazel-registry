"""Check public installation TARs against the owners' setup.py declarations."""
import argparse
import ast
import configparser
import hashlib
import json
from email.parser import BytesParser
from pathlib import Path
import tarfile
import unittest
import zipfile

from packaging.requirements import Requirement

parser = argparse.ArgumentParser()
parser.add_argument('--source', type=Path, required=True)
parser.add_argument('--wheels', nargs='+', type=Path, required=True)
parser.add_argument('--receipts', nargs='+', type=Path, required=True)
parser.add_argument('--runtime', nargs='+', required=True)
args, remaining = parser.parse_known_args()
SOURCE = args.source.absolute().parent.parent
SITE = 'usr/local/lib/python3.13/dist-packages/'


def setup_fields(path):
    tree = ast.parse(path.read_text())
    constants = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            try:
                constants[node.targets[0].id] = ast.literal_eval(node.value)
            except (ValueError, TypeError):
                pass
    call = next(n.value for n in tree.body if isinstance(n, ast.Expr)
                and isinstance(n.value, ast.Call) and isinstance(n.value.func, ast.Name)
                and n.value.func.id == 'setup')
    wanted = {'name', 'version', 'scripts', 'entry_points', 'install_requires', 'extras_require'}
    fields = {kw.arg: eval(compile(ast.Expression(kw.value), str(path), 'eval'),
                           {'__builtins__': {}}, constants)
              for kw in call.keywords if kw.arg in wanted}
    package_node = next((kw.value for kw in call.keywords if kw.arg == 'packages'), None)
    if isinstance(package_node, ast.Call):
        assert isinstance(package_node.func, ast.Name) and package_node.func.id == 'find_packages'
        packages = []
        for init in path.parent.rglob('__init__.py'):
            directory = init.parent
            parents = [directory, *list(directory.parents)[:len(directory.relative_to(path.parent).parts) - 1]]
            if all((parent / '__init__.py').is_file() for parent in parents):
                packages.append('.'.join(directory.relative_to(path.parent).parts))
        fields['packages'] = packages
    else:
        fields['packages'] = ast.literal_eval(package_node) if package_node else []
    return fields


class InstallationLayoutTest(unittest.TestCase):
    def test_original_setup_contract(self):
        wheels = {p.name: p for p in args.wheels}
        receipts = {r['distribution']: r for r in (json.loads(p.read_text()) for p in args.receipts)}
        observed = set()
        for archive in args.runtime:
            with self.subTest(archive=archive), tarfile.open(archive) as stream:
                members = {m.name.removeprefix('./'): m for m in stream if m.isfile()}
                headers = [p for p in members if p.endswith('.dist-info/METADATA')]
                self.assertEqual(len(headers), 1)
                header = headers[0]
                raw = stream.extractfile(members[header]).read()
                metadata = BytesParser().parsebytes(raw)
                name = metadata['Name']
                receipt = receipts.pop(name)
                wheel = wheels.pop(receipt['wheel']['filename'])
                self.assertEqual(receipt['wheel']['sha256'], hashlib.sha256(wheel.read_bytes()).hexdigest())
                self.assertEqual(receipt['wheel']['metadata_sha256'], hashlib.sha256(raw).hexdigest())
                with zipfile.ZipFile(wheel) as archive:
                    self.assertEqual(archive.read(header.removeprefix(SITE)), raw)
                self.assertNotIn(name, observed)
                observed.add(name)
                owner = SOURCE / name
                contract = setup_fields(owner / 'setup.py')
                self.assertEqual(name, contract['name'])
                self.assertEqual(metadata['Version'], contract['version'])
                expected_requires = list(contract.get('install_requires', []))
                for extra, requirements in contract.get('extras_require', {}).items():
                    expected_requires.extend(requirement + "; extra == '" + extra + "'" for requirement in requirements)
                self.assertEqual(set(map(Requirement, metadata.get_all('Requires-Dist', []))),
                                 set(map(Requirement, expected_requires)))
                for package in contract['packages']:
                    directory = owner / package.replace('.', '/')
                    for source in directory.glob('*.py'):
                        installed = SITE + str(source.relative_to(owner))
                        self.assertEqual(stream.extractfile(members[installed]).read(), source.read_bytes())
                for script in contract.get('scripts', []):
                    installed = 'usr/local/bin/' + Path(script).name
                    content = stream.extractfile(members[installed]).read()
                    self.assertEqual(content.split(b'\n', 1)[0], b'#!/usr/bin/python3')
                    self.assertEqual(content.split(b'\n', 1)[1], (owner / script).read_bytes().split(b'\n', 1)[1])
                entries = contract.get('entry_points', {}).get('console_scripts', [])
                if entries:
                    entry_path = header.rsplit('/', 1)[0] + '/entry_points.txt'
                    config = configparser.ConfigParser()
                    config.read_string(stream.extractfile(members[entry_path]).read().decode())
                    expected = dict(tuple(part.strip() for part in entry.split('=', 1)) for entry in entries)
                    self.assertEqual(dict(config['console_scripts']), expected)
                    for command in expected:
                        self.assertIn('usr/local/bin/' + command, members)
                for name, member in members.items():
                    self.assertEqual((member.uid, member.gid), (0, 0))
                    self.assertEqual(member.mode, 0o755 if name.startswith('usr/local/bin/') else 0o644)
        expected = {p.parent.name for p in SOURCE.glob('sonic-*/setup.py')}
        self.assertEqual(observed, expected)
        self.assertFalse(wheels)
        self.assertFalse(receipts)


if __name__ == '__main__':
    unittest.main(argv=[__file__, *remaining])
