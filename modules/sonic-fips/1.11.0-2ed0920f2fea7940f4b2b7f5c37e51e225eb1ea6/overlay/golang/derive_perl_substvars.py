"""Run the original dh_perl on the native compiler package payload."""
import argparse
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile

p = argparse.ArgumentParser()
for key in ('runtime', 'archive', 'control', 'changelog', 'output'):
    p.add_argument('--' + key, type=Path, required=True)
p.add_argument('--architecture', required=True, choices=('amd64', 'arm64'))
a = p.parse_args()
output = a.output.absolute()
runtime = a.runtime.absolute()
with tempfile.TemporaryDirectory(prefix='golang-perl-', dir=output.parent) as scratch:
    scratch = Path(scratch)
    debian = scratch / 'debian'
    package = 'golang-1.26-go'
    root = debian / package
    root.mkdir(parents=True)
    with tarfile.open(a.archive) as archive:
        # Only this component's declared TAR is accepted. Preserve the original
        # source-tree links: dh_perl does not traverse their other-package data.
        for member in archive.getmembers():
            if member.name.startswith('/') or '..' in Path(member.name).parts:
                raise ValueError('invalid compiler archive member: ' + member.name)
        archive.extractall(root, filter='fully_trusted')
    shutil.copyfile(a.control, debian / 'control')
    shutil.copyfile(a.changelog, debian / 'changelog')
    environment = {
        'PATH': str(runtime / 'bin'), 'HOME': str(scratch), 'TMPDIR': str(scratch),
        'LANG': 'C', 'LC_ALL': 'C', 'DPKG_NLS': '0',
        'DEB_HOST_ARCH': a.architecture, 'DEB_BUILD_ARCH': a.architecture,
    }
    subprocess.run([str(runtime / 'bin/dh_perl'), '-p' + package], cwd=scratch,
                   env=environment, check=True)
    variables = debian / (package + '.substvars')
    text = variables.read_text() if variables.exists() else ''
    # dh_perl emits no key when this package contains no Perl code. Original
    # dh_gencontrol treats that absence as an empty dependency. Make that actual
    # helper result explicit for runtime_packages' required substitution check.
    if not any(line.startswith('perl:Depends=') for line in text.splitlines()):
        if text and not text.endswith('\n'):
            text += '\n'
        text += 'perl:Depends=\n'
    output.write_text(text)
