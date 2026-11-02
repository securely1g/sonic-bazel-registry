"""Validate the registered owner wheel and install TAR in a source-free consumer."""

import ast
from email.parser import BytesParser
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tarfile
import tempfile
import venv
import zipfile

from installer import install
from installer.destinations import SchemeDictionaryDestination
from installer.sources import WheelFile


def main():
    wheel, setup, install_tar = [Path(arg).absolute() for arg in sys.argv[1:]]
    assert platform.machine() == 'x86_64'
    assert sys.version_info[:2] == (3, 13)
    tree = ast.parse(setup.read_text())
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
             and isinstance(node.func, ast.Name) and node.func.id == 'setup']
    assert len(calls) == 1
    arguments = {item.arg: item.value for item in calls[0].keywords}
    declarations = {target.id: node.value for node in tree.body if isinstance(node, ast.Assign)
                    for target in node.targets if isinstance(target, ast.Name)}
    package_call = arguments['packages']
    assert isinstance(package_call, ast.Call) and package_call.func.id == 'find_packages'
    assert [ast.literal_eval(value) for value in package_call.args] == ['src']
    assert ast.literal_eval(arguments['package_dir']) == {
        'sonic_ax_impl': 'src/sonic_ax_impl', 'ax_interface': 'src/ax_interface',
    }
    source_root = setup.parent / 'src'
    packages = []
    expected = {}
    for init in source_root.rglob('__init__.py'):
        directory = init.parent
        parents = [directory, *list(directory.parents)[:len(directory.relative_to(source_root).parts) - 1]]
        if not all((parent / '__init__.py').is_file() for parent in parents):
            continue
        packages.append(directory.relative_to(source_root).as_posix().replace('/', '.'))
        for path in directory.glob('*.py'):
            expected[path.relative_to(source_root).as_posix()] = path
    assert packages
    for package, patterns in ast.literal_eval(arguments['package_data']).items():
        for pattern in patterns:
            for path in (source_root / package.replace('.', '/')).glob(pattern):
                if path.is_file():
                    expected[path.relative_to(source_root).as_posix()] = path
    requirements = ast.literal_eval(declarations[arguments['install_requires'].id])
    with tempfile.TemporaryDirectory(dir=os.environ['TEST_TMPDIR']) as temporary:
        environment = Path(temporary) / 'installed'
        venv.EnvBuilder(with_pip=False).create(environment)
        python = environment / 'bin/python'
        scheme = json.loads(subprocess.check_output([
            str(python), '-I', '-c', 'import json,sysconfig;print(json.dumps(sysconfig.get_paths()))',
        ], text=True))
        scheme['headers'] = scheme['include']
        destination = SchemeDictionaryDestination(
            scheme, interpreter=str(python), script_kind='posix', bytecode_optimization_levels=(),
        )
        with WheelFile.open(wheel) as contents:
            install(source=contents, destination=destination, additional_metadata={'INSTALLER': b'registry-ci\n'})
        site = Path(scheme['purelib'])
        with zipfile.ZipFile(wheel) as archive:
            names = archive.namelist()
            assert {name for name in names if '.dist-info/' not in name} == set(expected)
            for name, source in expected.items():
                assert archive.read(name) == source.read_bytes() == (site / name).read_bytes(), name
            metadata = BytesParser().parsebytes(archive.read(next(name for name in names if name.endswith('.dist-info/METADATA'))))
            assert metadata['Name'] == ast.literal_eval(arguments['name']) == 'asyncsnmp'
            assert metadata['Version'] == ast.literal_eval(arguments['version']) == '2.1.0'
            assert {value.replace('_', '-') for value in metadata.get_all('Requires-Dist', [])} == {
                value.replace('_', '-') for value in requirements}
            assert {value.replace('_', '-') for value in metadata.get_all('Provides-Extra', [])} == {'high-perf'}
            assert len([name for name in names if name.endswith('/licenses/LICENSE')]) == 1
        with tarfile.open(install_tar) as archive:
            members = archive.getmembers()
            assert [member.name for member in members] == ['usr/share/snmp/sysDescr_pass.py']
            member = members[0]
            assert (member.uid, member.gid, member.mode, member.mtime) == (0, 0, 0o755, 0)
            assert archive.extractfile(member).read() == expected['sonic_ax_impl/bin/sysDescr_pass.py'].read_bytes()
        probe = r'''import importlib,importlib.metadata,json,pathlib,sys
site=pathlib.Path(sys.argv[1]).resolve()
modules=['ax_interface','ax_interface.encodings','ax_interface.protocol',
         'sonic_ax_impl','sonic_ax_impl.utils.arg_parser']
for name in modules:
    module=importlib.import_module(name)
    assert pathlib.Path(module.__file__).resolve().is_relative_to(site), module.__file__
from ax_interface.encodings import ObjectIdentifier
value=ObjectIdentifier.from_iterable((1,3,6,1,2,1,1,5,0))
assert str(ObjectIdentifier.from_bytes(value.to_bytes('!'),'!'))=='.1.3.6.1.2.1.1.5.0'
assert importlib.metadata.version('asyncsnmp')=='2.1.0'
print(json.dumps({'modules':modules,'agentx_oid_roundtrip':str(value)}))
'''
        result = subprocess.run([str(python), '-I', '-c', probe, str(site)], cwd=temporary,
                                capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, result.stdout + result.stderr
        output = Path(os.environ['TEST_UNDECLARED_OUTPUTS_DIR'])
        output.mkdir(parents=True, exist_ok=True)
        (output / 'registered-wheel.json').write_text(json.dumps({
            'status': 'passed', 'architecture': platform.machine(), 'python': platform.python_version(),
            'source_revision': '5445b3138b586f988472a0840f274cae101996af',
            'wheel': wheel.name, 'wheel_sha256': hashlib.sha256(wheel.read_bytes()).hexdigest(),
            'install_tar_sha256': hashlib.sha256(install_tar.read_bytes()).hexdigest(),
            'packages': len(packages), 'payload_files': len(expected),
            'installed_probe': json.loads(result.stdout),
            'scope': 'Registered wheel/TAR bytes, metadata and installed AgentX interfaces; full Common/Redis/snmpd queries are covered by source CI',
        }, indent=2) + '\n')


if __name__ == '__main__':
    main()
