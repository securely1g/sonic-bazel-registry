"""Run both original upstream class lists with Python's supported loader API."""
import importlib
from pathlib import Path
import platform
import sys
import sysconfig
import unittest


def run_upstream(expected_root=None):
    assert sys.implementation.name == "cpython" and sys.version_info[:2] == (3, 13)
    assert platform.machine() == "x86_64" and sys.platform == "linux"
    assert not sysconfig.get_config_var("Py_GIL_DISABLED")
    import bitarray
    from bitarray import test_bitarray, test_util
    assert bitarray.__version__ == "2.8.1"
    for name in ("_bitarray", "_util"):
        module = importlib.import_module("bitarray." + name)
        assert Path(module.__file__).name == name + ".cpython-313-x86_64-linux-gnu.so"
        if expected_root is not None:
            assert Path(module.__file__).resolve().is_relative_to(expected_root.resolve())
    if expected_root is not None:
        for module in (bitarray, test_bitarray, test_util):
            assert Path(module.__file__).resolve().is_relative_to(expected_root.resolve())
    # Upstream run() uses these exact two lists. Use TestLoader instead of the
    # removed unittest.makeSuite; no class, method, skip or expectation is altered.
    classes = list(test_bitarray.tests) + list(test_util.tests)
    assert test_bitarray.tests and test_util.tests
    suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(cls)
                               for cls in classes)
    assert suite.countTestCases() > 0
    endian = bitarray.get_default_endian()
    try:
        return unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful()
    finally:
        bitarray._set_default_endian(endian)


if __name__ == "__main__":
    raise SystemExit(0 if run_upstream() else 1)
