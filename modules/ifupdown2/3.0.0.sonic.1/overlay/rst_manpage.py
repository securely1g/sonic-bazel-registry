"""The source genmanpages.sh command, using declared APT docutils and pigz."""
from pathlib import Path
import subprocess
import sys
from docutils.core import publish_string

source, output, pigz = sys.argv[1:]
page = publish_string(Path(source).read_bytes(), source_path=source,
                      writer_name='manpage', settings_overrides={'halt_level': 2})
with open(output, 'wb') as stream:
    subprocess.run([pigz, '-n', '-c'], input=page, stdout=stream, check=True)
