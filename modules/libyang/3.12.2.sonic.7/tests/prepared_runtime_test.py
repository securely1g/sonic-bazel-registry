"""Transport/launcher regressions; real native/ARM contracts remain separate CI."""

import importlib.util
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile
from types import SimpleNamespace
import unittest


OVERLAY = Path(__file__).resolve().parents[1] / "overlay"
spec = importlib.util.spec_from_file_location("capture_test_runtime", OVERLAY / "capture_test_runtime.py")
capture_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(capture_module)


class RuntimeCaptureTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="libyang-runtime-test-")
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.runtime = self.root / "validated"
        self.runtime.mkdir()
        # Synthetic headers exercise this transport's architecture guard only;
        # the original infra validator performs complete ELF/closure checking.
        self.elf = bytearray(32)
        self.elf[:6] = b"\x7fELF\x02\x01"
        struct.pack_into("<H", self.elf, 18, 183)
        self.binary = self.root / "original-binary"
        self.binary.write_bytes(self.elf)
        for relative in ("ld-linux-aarch64.so.1", "libone.so.1", ".debug/libone.so.1.debug"):
            path = self.runtime / relative
            path.parent.mkdir(exist_ok=True)
            path.write_bytes(self.elf)
            path.chmod(0o755 if not relative.startswith(".debug/") else 0o644)
        self.template = self.root / "launcher.in"
        self.template.write_text("#!/bin/sh\nexec runtime/@@LOADER@@ \"$@\"\n")
        self.validator = self.root / "validator.py"
        self.validator.write_text("# exact declared validator input\n")
        self.args = SimpleNamespace(
            machine=183, command=[str(self.runtime / "ld-linux-aarch64.so.1"), "--inhibit-cache", "--library-path", str(self.runtime), str(self.binary)],
            runtime=self.root / "output", manifest=self.root / "output.json", launcher=self.root / "launcher",
            template=self.template, validator=self.validator,
        )

    def test_exact_relocatable_capture_does_not_copy_original_binary(self):
        capture_module.capture(self.args)
        manifest = json.loads(self.args.manifest.read_text())
        self.assertEqual(manifest["target_machine"], 183)
        self.assertNotIn(str(self.root), self.args.manifest.read_text())
        self.assertEqual(len(manifest["files"]), 3)
        self.assertFalse((self.args.runtime / self.binary.name).exists())
        for item in manifest["files"]:
            copied = self.args.runtime / item["path"]
            self.assertEqual(copied.read_bytes(), (self.runtime / item["path"]).read_bytes())
            self.assertEqual(copied.stat().st_mode & 0o777, item["mode"])
            self.assertEqual(capture_module.digest(copied), item["sha256"])
        self.assertIn("ld-linux-aarch64.so.1", self.args.launcher.read_text())
        self.assertTrue(self.args.launcher.stat().st_mode & 0o111)

    def test_wrong_binary_cpu_rejected(self):
        struct.pack_into("<H", self.elf, 18, 62)
        self.binary.write_bytes(self.elf)
        with self.assertRaisesRegex(ValueError, "architecture"):
            capture_module.capture(self.args)
        self.assertFalse(self.args.runtime.exists())

    def test_wrong_library_cpu_rejected(self):
        struct.pack_into("<H", self.elf, 18, 62)
        (self.runtime / "libone.so.1").write_bytes(self.elf)
        with self.assertRaisesRegex(ValueError, "architecture"):
            capture_module.capture(self.args)
        self.assertFalse(self.args.runtime.exists())

    def test_runtime_symlink_rejected(self):
        (self.runtime / "foreign-link").symlink_to(self.binary)
        with self.assertRaisesRegex(ValueError, "regular files"):
            capture_module.capture(self.args)
        self.assertFalse(self.args.runtime.exists())

    def test_unexpected_validator_command_rejected(self):
        self.args.command[1] = "--inhibit-rpath"
        with self.assertRaisesRegex(ValueError, "exact loader"):
            capture_module.capture(self.args)
        self.assertFalse(self.args.runtime.exists())

    def test_existing_output_is_not_overwritten(self):
        self.args.runtime.mkdir()
        existing = self.args.runtime / "old"
        existing.write_text("retain")
        with self.assertRaisesRegex(ValueError, "not empty"):
            capture_module.capture(self.args)
        self.assertEqual(existing.read_text(), "retain")


class LauncherTest(unittest.TestCase):
    def test_original_binary_cwd_arguments_and_environment_survive(self):
        with tempfile.TemporaryDirectory(prefix="libyang-launcher-test-") as temporary:
            root = Path(temporary)
            runfiles = root / "test.runfiles"
            runtime = runfiles / "module/runtime"
            runtime.mkdir(parents=True)
            tools = runfiles / "tools"
            tools.mkdir()
            resolver = tools / "realpath"
            compiler = os.environ.get("PREPARED_RUNTIME_TEST_CC", "/usr/bin/cc")
            compile_result = subprocess.run([compiler, "-static", "-O2", "-Wall", "-Wextra", "-Werror", str(OVERLAY / "test_runtime_realpath.c"), "-o", str(resolver)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30)
            self.assertEqual(compile_result.returncode, 0, compile_result.stdout.decode())
            elf = resolver.read_bytes()
            self.assertEqual(elf[:6], b"\x7fELF\x02\x01")
            phoff = struct.unpack_from("<Q", elf, 32)[0]
            phentsize, phnum = struct.unpack_from("<HH", elf, 54)
            self.assertNotIn(3, [struct.unpack_from("<I", elf, phoff + index * phentsize)[0] for index in range(phnum)], "resolver must not require a dynamic loader")
            real_binary = root / "original binary"
            real_binary.write_text("original target; not executed by this launcher unit test")
            (runfiles / "module/binary").symlink_to(real_binary)
            loader = runtime / "loader"
            recorder = "import json,os,sys;open(os.environ['RESULT_FILE'],'w').write(json.dumps({'argv':sys.argv[1:],'cwd':os.getcwd(),'env':dict(os.environ)}))"
            loader.write_text("#!/bin/sh\nexec /usr/bin/python3 -I -S -c '" + recorder.replace("'", "'\\''") + "' \"$@\"\n")
            loader.chmod(0o755)
            script = (OVERLAY / "prepared_test_runtime.sh.in").read_text()
            for old, new in {"@@REALPATH@@": "tools/realpath", "@@BINARY@@": "module/binary", "@@RUNTIME@@": "module/runtime", "@@LOADER@@": "loader"}.items():
                script = script.replace(old, new)
            launcher = root / "launcher"
            launcher.write_text(script)
            launcher.chmod(0o755)
            cwd = root / "caller directory"
            cwd.mkdir()
            result = root / "result.json"
            poison = root / "poison-python-path"
            poison.mkdir()
            (poison / "sitecustomize.py").write_text("raise RuntimeError('test CLI must not start a preparation interpreter')\n")
            environment = dict(os.environ, RUNFILES_DIR=str(runfiles), RESULT_FILE=str(result), PYTHONHOME="original-target-home", PYTHONPATH=str(poison), PYTHONINSPECT="1", PYTHONMALLOC="invalid-poison-value", ORIGINAL_EMPTY="", LD_LIBRARY_PATH="must-not-reach-target", LD_PRELOAD="", LD_AUDIT="")
            arguments = ["a b", "", "--option", "line\nbreak"]
            completed = subprocess.run([str(launcher), *arguments], cwd=cwd, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
            self.assertEqual(completed.returncode, 0, completed.stderr.decode())
            observed = json.loads(result.read_text())
            self.assertEqual(observed["argv"], ["--inhibit-cache", "--library-path", str(runtime), str(real_binary), *arguments])
            self.assertEqual(observed["cwd"], str(cwd))
            self.assertEqual(observed["env"]["PYTHONHOME"], "original-target-home")
            self.assertEqual(observed["env"]["PYTHONPATH"], str(poison))
            self.assertEqual(observed["env"]["PYTHONINSPECT"], "1")
            self.assertEqual(observed["env"]["PYTHONMALLOC"], "invalid-poison-value")
            self.assertEqual(observed["env"]["ORIGINAL_EMPTY"], "")
            for name in ("LD_LIBRARY_PATH", "LD_PRELOAD", "LD_AUDIT"):
                self.assertNotIn(name, observed["env"])


if __name__ == "__main__":
    unittest.main()
