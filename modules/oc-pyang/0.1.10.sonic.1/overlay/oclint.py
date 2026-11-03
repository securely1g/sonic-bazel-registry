"""Run the unchanged CLI shipped in pyang's locked wheel with the OC plugin."""
from pathlib import Path
import sys
import zipfile
import pyang
import openconfig

# pyang 2.4 ships a wheel script, not a console_scripts entry point. Its wheel
# is explicit runfile data; execute that original script with the declared SDK.
wheel_root = Path(pyang.__file__).parent.parent.parent
wheels = list(wheel_root.glob("pyang-*.whl"))
if len(wheels) != 1:
    raise RuntimeError("Exactly one declared pyang wheel is required")
sys.argv[1:1] = ["--plugindir", str(Path(openconfig.__file__).parent)]
with zipfile.ZipFile(wheels[0]) as archive:
    scripts = [name for name in archive.namelist() if name.endswith(".data/scripts/pyang")]
    if len(scripts) != 1:
        raise RuntimeError("The pinned wheel must provide its original pyang script")
    code = compile(archive.read(scripts[0]), scripts[0], "exec")
exec(code, {"__name__": "__main__", "__file__": scripts[0]})
