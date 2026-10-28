"""Default config and plugin lookups must agree with the installed TAR layout."""
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tarfile

probe = str(Path(sys.argv[1]).absolute())
with tarfile.open(sys.argv[2]) as archive:
    configs = [member.name.removeprefix("./") for member in archive if member.name.endswith("/pktloc")]
with tarfile.open(sys.argv[3]) as archive:
    plugins = [member.name.removeprefix("./") for member in archive if member.name.endswith("/cli/qdisc/bfifo.so")]
assert len(configs) == len(plugins) == 1, (configs, plugins)
environment = dict(os.environ, NLDBG="2")
environment.pop("NLSYSCONFDIR", None)
config = subprocess.run([probe, "config"], env=environment, capture_output=True, text=True)
assert config.returncode == 0, config.stderr
assert "/" + configs[0] in config.stderr, (configs[0], config.stderr)
plugin = subprocess.run([probe, "plugin"], env=environment, capture_output=True, text=True)
expected = "/" + str(PurePosixPath(plugins[0]).parent / "__libnl3_missing_path_probe__.so")
assert plugin.returncode != 0 and expected in plugin.stderr, (expected, plugin.returncode, plugin.stderr)
