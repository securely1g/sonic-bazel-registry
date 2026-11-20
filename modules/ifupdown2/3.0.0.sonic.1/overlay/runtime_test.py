"""Read installed archive/control formats and exercise the original parser."""
import ast
from email.parser import Parser
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile

payload, metadata, control, setup_path = map(Path, sys.argv[1:])
record = json.loads(metadata.read_text())['packages']['ifupdown2']
with tarfile.open(control) as archive:
    fields = Parser().parsestr(archive.extractfile('control').read().decode())
    assert fields['Package'] == 'ifupdown2' and fields['Version'] == '3.0.0-1'
    assert fields['Architecture'] == 'all'
    assert 'python3' in fields['Depends'] and 'iproute2' in fields['Depends'] and '${' not in fields['Depends']
    assert {'postinst', 'postrm', 'prerm', 'conffiles'} <= set(archive.getnames())
with tempfile.TemporaryDirectory() as temporary, tarfile.open(payload) as archive:
    root = Path(temporary)
    members = {member.name.removeprefix('./'): member for member in archive}
    assert members['sbin/ifup'].issym() and members['sbin/ifup'].linkname == '/usr/share/ifupdown2/ifupdown2'
    assert members['usr/share/ifupdown2/ifupdown2'].linkname == '__main__.py'
    main = members['usr/share/ifupdown2/__main__.py']
    assert main.mode == 0o755 and archive.extractfile(main).readline() == b'#!/usr/bin/python3\n'
    assert members['usr/share/doc/ifupdown2/examples/generate_interfaces.py'].mode == 0o755
    assert members['usr/share/doc/ifupdown2/examples/batman_adv/configure_batman_adv.sh'].mode == 0o755
    for member in members.values():
        if member.isfile():
            target = root / member.name.removeprefix('./'); target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.extractfile(member).read())
    pkg = Parser().parsestr((root/'usr/share/ifupdown2-3.0.0.egg-info/PKG-INFO').read_text())
    setup = ast.parse(setup_path.read_text())
    call = next(node for node in ast.walk(setup) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'setup')
    values = {keyword.arg: ast.literal_eval(keyword.value) for keyword in call.keywords if isinstance(keyword.value, (ast.Constant, ast.List))}
    for field, source in [('Name','name'),('Version','version'),('Summary','description'),('Author','author'),('License','license'),('Home-page','url')]:
        assert pkg[field] == values[source]
    assert pkg.get_all('Classifier') == values['classifiers']
    environment = dict(os.environ, PYTHONPATH=str(root/'usr/share'), PYTHONDONTWRITEBYTECODE='1')
    entry = root/'ifquery'; entry.symlink_to('usr/share/ifupdown2/__main__.py')
    result = subprocess.run([sys.executable, str(entry), '--help'], env=environment, check=True, capture_output=True, text=True)
    assert 'usage:' in result.stdout and 'ifquery' in result.stdout
    sys.path.insert(0, str(root/'usr/share'))
    import ifupdown2.ifupdown.main as main_module
    main_module.IFUPDOWN2_CONF_PATH = str(root/'etc/network/ifupdown2/ifupdown2.conf')
    manager = main_module.Ifupdown2(daemon=False, uid=os.geteuid())
    manager.read_config()
    assert main_module.configmap_g['use_daemon'] == 'no'
    assert main_module.configmap_g['template_engine'] == 'mako'
    from ifupdown2.ifupdown.networkinterfaces import networkInterfaces
    parser = networkInterfaces(template_enable='0')
    interfaces = []
    parser.subscribe('iface_found', interfaces.append)
    parser.read_filedata('auto lo mgmt0\niface lo inet loopback\niface mgmt0 inet static\n    address 192.0.2.10/24\n    gateway 192.0.2.1\n')
    assert parser.errors == 0 and {iface.name for iface in interfaces} == {'lo', 'mgmt0'}
    mgmt = next(iface for iface in interfaces if iface.name == 'mgmt0')
    assert mgmt.get_attr_value_first('address') == '192.0.2.10/24'
    assert mgmt.get_attr_value_first('gateway') == '192.0.2.1'
print('ifupdown2 runtime/control, ifquery --help, original config parser passed')

print('Installed parser interpreter:', sys.version, sys.executable)
