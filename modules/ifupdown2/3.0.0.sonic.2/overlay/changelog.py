"""Ask the locked Debian helper for the installed changelog, without packaging."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from runtime_packages import DebianTools

control, changelog, compat, tools, pigz, output, architecture = sys.argv[1:]
with tempfile.TemporaryDirectory(dir='.') as temporary:
    root = Path(temporary).resolve()
    debian = root / 'debian'; debian.mkdir()
    for name, source in [('control', control), ('changelog', changelog), ('compat', compat)]:
        shutil.copyfile(source, debian / name)
    (debian / 'ifupdown2').mkdir()
    DebianTools(Path(tools).resolve(), root, architecture).run('dh_installchangelogs', '-pifupdown2')
    installed = debian / 'ifupdown2/usr/share/doc/ifupdown2/changelog.Debian'
    with installed.open('rb') as source, open(output, 'wb') as destination:
        subprocess.run([pigz, '-n', '-c'], stdin=source, stdout=destination, check=True)
