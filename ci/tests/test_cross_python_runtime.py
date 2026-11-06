"""Keep test-only ARM Python mappings pinned to the declared interpreter ABI."""

import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock


SPEC = importlib.util.spec_from_file_location(
    "registry_ci_python_runtime", Path(__file__).resolve().parents[1] / "registry_ci.py")
registry_ci = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(registry_ci)


class CrossPythonRuntimeTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.base = self.root / "output"
        self.consumer = self.root / "consumer"
        self.artifacts = self.root / "artifacts"
        self.consumer.mkdir()
        self.artifacts.mkdir()
        self.native = self.base / "external/rules_python++python+python_3_11_x86_64-unknown-linux-gnu"
        self.arm = self.base / "external/rules_python++python+python_3_11_aarch64-unknown-linux-gnu"
        self.runtime(self.native, 62)
        self.executor = ["/usr/local/bin/sonic-arm64", "--bind", str(self.root), "--"]
        self.commands = []
        self.arm_overrides = {}

    def runtime(self, root, machine):
        (root / "bin").mkdir(parents=True)
        (root / "lib").mkdir()
        (root / "STANDALONE_INTERPRETER").touch()
        header = bytearray(64)
        header[:6] = b"\x7fELF\x02\x01"
        header[18:20] = machine.to_bytes(2, "little")
        executable = root / "bin/python3"
        executable.write_bytes(header)
        executable.chmod(0o755)
        (root / "lib/libpython3.11.so.1.0").write_bytes(b"runtime library " + str(machine).encode())

    def execute(self, command, cwd, log):
        self.commands.append(command)
        if "fetch" in command:
            self.runtime(self.arm, 183)
        if log.suffix == ".json":
            arm = log.name.endswith("-arm.json")
            identity = {"machine": "aarch64" if arm else "x86_64",
                        "version": [3, 11, 14, "final", 0], "implementation": "cpython",
                        "cache_tag": "cpython-311", "abiflags": ""}
            if arm:
                identity.update(self.arm_overrides)
            log.write_text(json.dumps(identity))
        else:
            log.write_text("fixture command\n")

    def prepare(self):
        flags = ["--registry=file:///registry", "--lockfile_mode=update",
                 *registry_ci.HTTP_DOWNLOAD_FLAGS, "--jobs=1", "--discard_analysis_cache",
                 "--platforms=@platforms//:arm64", "--host_platform=@platforms//:amd64"]
        with mock.patch.object(registry_ci, "run_logged", side_effect=self.execute):
            return registry_ci.prepare_cross_python_runtimes(
                ["bazel", "--host_jvm_args=-Xmx2g"], flags, ["@module//:test"], self.base,
                self.consumer, self.artifacts, self.executor)

    def test_maps_the_locked_arm_peer_without_changing_native_runtime(self):
        original = (self.native / "bin/python3").read_bytes()
        mappings = self.prepare()
        self.assertEqual(len(mappings), 1)
        mapping = mappings[0]
        self.assertEqual(mapping["source"], str(self.arm))
        self.assertEqual(mapping["destination"], str(self.native))
        self.assertEqual(mapping["native"]["elf_machine"], 62)
        self.assertEqual(mapping["arm"]["elf_machine"], 183)
        self.assertEqual(mapping["native"]["version"], mapping["arm"]["version"])
        self.assertEqual(mapping["native"]["interpreter_sha256"], hashlib.sha256(original).hexdigest())
        self.assertEqual((self.native / "bin/python3").read_bytes(), original)
        self.assertEqual(json.loads((self.artifacts / "cross-python-runtimes.json").read_text()), mappings)
        fetch = next(command for command in self.commands if "fetch" in command)
        self.assertIn("--repo=@@" + self.arm.name, fetch)
        self.assertIn("--host_jvm_args=-Xmx2g", fetch)
        self.assertTrue(set(registry_ci.HTTP_DOWNLOAD_FLAGS).issubset(fetch))
        self.assertFalse(any(flag.startswith(("--platforms=", "--host_platform=", "--jobs=")) for flag in fetch))
        self.assertNotIn("--discard_analysis_cache", fetch)
        probes = [command for command in self.commands if "-c" in command]
        self.assertEqual(probes[0][0], str(self.native / "bin/python3"))
        self.assertEqual(probes[1][:len(self.executor)], self.executor)

    def test_rejects_a_different_locked_python_version(self):
        self.arm_overrides["version"] = [3, 11, 13, "final", 0]
        with self.assertRaisesRegex(registry_ci.RegistryError, "version and ABI"):
            self.prepare()
        self.assertFalse((self.artifacts / "cross-python-runtimes.json").exists())

    def test_rejects_an_incompatible_python_abi(self):
        self.arm_overrides["abiflags"] = "d"
        with self.assertRaisesRegex(registry_ci.RegistryError, "version and ABI"):
            self.prepare()

    def test_rejects_an_arm_interpreter_that_reports_native_execution(self):
        self.arm_overrides["machine"] = "x86_64"
        with self.assertRaisesRegex(registry_ci.RegistryError, "actual architecture"):
            self.prepare()

    def test_rejects_wrong_elf_before_executing_it(self):
        executable = self.native / "bin/python3"
        header = bytearray(executable.read_bytes())
        header[18:20] = (183).to_bytes(2, "little")
        executable.write_bytes(header)
        with mock.patch.object(registry_ci, "run_logged") as execute:
            with self.assertRaisesRegex(registry_ci.RegistryError, "ELF architecture"):
                registry_ci.python_runtime_identity(self.native, self.consumer, self.artifacts / "probe.json")
        execute.assert_not_called()

    def test_rejects_interpreter_symlink_outside_the_declared_runtime(self):
        executable = self.native / "bin/python3"
        outside = self.root / "outside-python"
        executable.rename(outside)
        executable.symlink_to(outside)
        with mock.patch.object(registry_ci, "run_logged") as execute:
            with self.assertRaisesRegex(registry_ci.RegistryError, "escapes its runtime"):
                registry_ci.python_runtime_identity(self.native, self.consumer, self.artifacts / "probe.json")
        execute.assert_not_called()


if __name__ == "__main__":
    unittest.main()
