"""Exercise the registered owner wheel from a source-free installed environment."""

import ast
from email.parser import BytesParser
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import venv
import zipfile

from installer import install
from installer.destinations import SchemeDictionaryDestination
from installer.sources import WheelFile


def main():
    wheel, setup = [Path(arg).absolute() for arg in sys.argv[1:]]
    assert platform.machine() == "x86_64"
    assert sys.version_info[:2] == (3, 13)
    # Read the owner's literal package contract without executing its setup.py
    # prerequisite checks or importing a second copy of the library.
    calls = [node for node in ast.walk(ast.parse(setup.read_text()))
             if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
             and node.func.id == "setup"]
    assert len(calls) == 1
    arguments = {value.arg: value.value for value in calls[0].keywords}
    packages = ast.literal_eval(arguments["packages"])
    expected = {}
    for package in packages:
        directory = setup.parent / package.replace(".", "/")
        files = list(directory.glob("*.py"))
        assert files, package
        expected.update({str(path.relative_to(setup.parent)): path for path in files})

    with tempfile.TemporaryDirectory(dir=os.environ["TEST_TMPDIR"]) as temporary:
        environment = Path(temporary) / "installed"
        venv.EnvBuilder(with_pip=False).create(environment)
        python = environment / "bin/python"
        scheme = json.loads(subprocess.check_output([
            str(python), "-I", "-c", "import json,sysconfig;print(json.dumps(sysconfig.get_paths()))",
        ], text=True))
        scheme["headers"] = scheme["include"]
        destination = SchemeDictionaryDestination(
            scheme, interpreter=str(python), script_kind="posix", bytecode_optimization_levels=(),
        )
        with WheelFile.open(wheel) as source:
            install(source=source, destination=destination, additional_metadata={"INSTALLER": b"registry-ci\n"})
        site = Path(scheme["purelib"])
        with zipfile.ZipFile(wheel) as archive:
            names = archive.namelist()
            actual = {name for name in names if name.endswith(".py") and ".dist-info/" not in name}
            assert actual == set(expected), (actual, set(expected))
            for name, source in expected.items():
                assert archive.read(name) == source.read_bytes() == (site / name).read_bytes(), name
            metadata = BytesParser().parsebytes(archive.read(next(name for name in names if name.endswith(".dist-info/METADATA"))))
            assert metadata["Name"].replace("_", "-") == "sonic-platform-common"
            assert metadata["Version"] == "1.0"
            assert set(metadata.get_all("Requires-Dist", [])) == {
                "natsort", "PyYAML", "sonic-py-common", "sonic-config-engine",
            }
        # These public peripheral interfaces require only this owner's wheel.
        # Config-engine/Common-dependent interfaces are covered in owner CI.
        probe = r'''import importlib,importlib.metadata,json,pathlib,sys
site=pathlib.Path(sys.argv[1]).resolve()
modules=['sonic_led.led_control_base','sonic_fan.fan_base',
         'sonic_eeprom.eeprom_base','sonic_y_cable.y_cable_base']
for name in modules:
    module=importlib.import_module(name)
    assert pathlib.Path(module.__file__).resolve().is_relative_to(site), module.__file__
from sonic_led.led_control_base import LedControlBase
from sonic_fan.fan_base import FanBase
from sonic_eeprom.eeprom_base import EepromDecoder
from sonic_y_cable.y_cable_base import YCableBase
assert FanBase().get_num_fans()==0
assert FanBase().get_status(1) is False
assert LedControlBase().port_link_state_change('Ethernet0','up') is None
fixture=pathlib.Path('eeprom.bin')
fixture.write_bytes(bytes(range(32)))
eeprom=EepromDecoder(str(fixture),[('data','s',8)],4,'',True)
assert eeprom.check_status()=='ok' and eeprom.is_read_only()
assert eeprom.read_eeprom()==bytearray(range(4,12))
assert eeprom.read_eeprom_bytes(4,offset=2)==bytearray(range(6,10))
assert [YCableBase.TARGET_NIC,YCableBase.TARGET_TOR_A,YCableBase.TARGET_TOR_B]==[0,1,2]
assert importlib.metadata.version('sonic-platform-common')=='1.0'
print(json.dumps({'modules':modules}))
'''
        result = subprocess.run([str(python), "-I", "-c", probe, str(site)], cwd=temporary,
                                capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, result.stdout + result.stderr
        output = Path(os.environ["TEST_UNDECLARED_OUTPUTS_DIR"])
        output.mkdir(parents=True, exist_ok=True)
        (output / "registered-wheel.json").write_text(json.dumps({
            "status": "passed", "architecture": platform.machine(),
            "python": platform.python_version(), "wheel": wheel.name,
            "sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
            "source_revision": "f933850f613036aea22c8aad42eda24134c291d0",
            "packages": len(set(packages)), "python_files": len(expected),
            "installed_probe": json.loads(result.stdout),
            "scope": "Complete owner wheel payload/metadata and installed LED/fan/EEPROM/Y-cable APIs; Common/config-engine runtime is covered by source CI",
        }, indent=2) + "\n")


if __name__ == "__main__":
    main()
