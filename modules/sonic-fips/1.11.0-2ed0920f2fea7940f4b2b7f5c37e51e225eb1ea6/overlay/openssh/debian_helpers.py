"""Preserve original Debian helper fragments through the public metadata inputs."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

p = argparse.ArgumentParser()
p.add_argument('--architecture', required=True)
p.add_argument('--package', required=True, choices=['openssh-client', 'openssh-server'])
p.add_argument('--payload', required=True)
p.add_argument('--control', required=True)
p.add_argument('--changelog', required=True)
p.add_argument('--runtime', required=True)
p.add_argument('--substvars-source')
p.add_argument('--output-substvars', required=True)
p.add_argument('--fragment', action='append', default=[])
p.add_argument('--runit-source')
p.add_argument('--runit-autoscripts')
p.add_argument('--debian-file', action='append', default=[])
p.add_argument('--output-control')
a = p.parse_args()
paths = {name:str(Path(getattr(a, name)).absolute()) for name in ['payload','control','changelog','runtime','output_substvars']}
outputs = {name:Path(path).absolute() for name,path in (value.split('=',1) for value in a.fragment)}
extra = Path(a.substvars_source).read_bytes() if a.substvars_source else b''
commands = [['dh_installsysusers'], ['dh_installtmpfiles']] if a.package == 'openssh-server' else [['dh_installtmpfiles'], ['dh_installsystemduser']]
if a.runit_source:
    commands = [['dh_installdebconf'], ['dh_installinit', '-R', '--name=ssh'], ['dh_installsysusers'], ['dh_installtmpfiles'], ['dh_installsystemd', 'ssh.service'], ['dh_installsystemd', '--no-enable', 'ssh.socket'], ['dh_installsystemd', '--no-start', 'rescue-ssh.target'], ['dh_installsystemd', 'sshd-keygen.service']]
build_arch = json.loads((Path(paths['runtime'])/'kernel-runtime.json').read_text())['architecture']
env = dict(os.environ, PATH=str(Path(paths['runtime'])/'bin'), LC_ALL='C', DEB_HOST_ARCH=a.architecture, DEB_BUILD_ARCH=build_arch)
with tempfile.TemporaryDirectory(prefix='openssh-debian-helpers-') as scratch:
    root = Path(scratch)
    if a.runit_source:
        from runtime_packages import tool_environment
        env = tool_environment(Path(paths['runtime']), root, a.architecture)
    debian = root/'debian'
    target = debian/a.package
    target.mkdir(parents=True)
    shutil.copyfile(paths['control'], debian/'control')
    shutil.copyfile(paths['changelog'], debian/'changelog')
    subprocess.run([str(Path(paths['runtime'])/'bin/tar'), '-xf', paths['payload'], '-C', str(target)], env=env, check=True)
    for entry in a.debian_file:
        name, filename = entry.split('=', 1)
        destination = debian/name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(Path(filename).absolute(), destination)
    for command in commands:
        subprocess.run([str(Path(paths['runtime'])/'bin'/command[0]), '-p'+a.package] + command[1:], cwd=root, env=env, check=True)
    if a.runit_source:
        subprocess.run([str(Path(paths['runtime'])/'bin/perl'), str(Path(a.runit_autoscripts).absolute()), str(Path(a.runit_source).absolute().parent), '-p'+a.package], cwd=root, env=env, check=True)
        subprocess.run([str(Path(paths['runtime'])/'bin/dh_installdeb'), '-p'+a.package], cwd=root, env=env, check=True)
    for script, output in outputs.items():
        source = target/'DEBIAN'/script if a.runit_source else debian/(a.package+'.'+script+'.debhelper')
        if not source.is_file():
            raise RuntimeError('Original helpers did not produce '+str(source))
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, output)
    variables = debian/(a.package+'.substvars')
    if not variables.is_file():
        raise RuntimeError('Original helpers did not produce package substitutions')
    substitutions = variables.read_bytes()+extra
    if a.runit_source:
        # Only misc values collide with runtime_packages' automatic debconf pass.
        # Preserve other stanzas byte-for-byte; retain its original shlibs pass.
        misc = {}
        remaining = []
        for line in substitutions.decode().splitlines(True):
            key, value = line.rstrip('\n').split('=', 1)
            if key.startswith('misc:'):
                misc[key] = value
            else:
                remaining.append(line)
        original_control = Path(paths['control']).read_text()
        paragraphs = original_control.split('\n\n')
        for index, paragraph in enumerate(paragraphs):
            if ('\n'+paragraph+'\n').find('\nPackage: '+a.package+'\n') >= 0:
                for key, value in misc.items():
                    paragraph = paragraph.replace('${'+key+'}', value)
                paragraphs[index] = paragraph
        Path(a.output_control).absolute().write_text('\n\n'.join(paragraphs))
        substitutions = ''.join(remaining).encode()
    Path(paths['output_substvars']).write_bytes(substitutions)
