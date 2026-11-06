"""Build a source-bound, portable audit JAR without per-job tool downloads."""
import hashlib
import importlib.util
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock
import zipfile

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("build_http_audit", ROOT / "ci/build_http_audit.py")
BUILD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILD)


class HttpAuditBuildTest(unittest.TestCase):
    def test_system_javac_is_used_without_installing_tools(self):
        with mock.patch.object(BUILD.shutil, "which", side_effect=lambda name: "/jdk/bin/" + name):
            self.assertEqual(BUILD.compiler_command(), ["/jdk/bin/javac"])

    def test_system_java_compiler_module_works_without_a_javac_launcher(self):
        with mock.patch.object(BUILD.shutil, "which", side_effect=lambda name: "/usr/bin/java" if name == "java" else None):
            self.assertEqual(BUILD.compiler_command(), ["/usr/bin/java", "-m", "jdk.compiler/com.sun.tools.javac.Main"])

    def test_missing_java_is_an_explicit_local_error(self):
        with mock.patch.object(BUILD.shutil, "which", return_value=None):
            with self.assertRaisesRegex(RuntimeError, "No system Java compiler"):
                BUILD.compiler_command()

    def test_failed_compilation_preserves_existing_artifact(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "DebianHttpAudit.java"
            source.write_text("invalid Java")
            output = Path(directory) / "agent.jar"
            output.write_bytes(b"previous-good-artifact")
            with mock.patch.object(BUILD, "compiler_command", return_value=["compiler"]), \
                 mock.patch.object(BUILD.subprocess, "run", side_effect=subprocess.CalledProcessError(1, "compiler")):
                with self.assertRaises(subprocess.CalledProcessError):
                    BUILD.build(source, output)
            self.assertEqual(output.read_bytes(), b"previous-good-artifact")

    def test_real_agent_has_exact_source_digest_portable_classes_and_stable_archive(self):
        try:
            compiler = BUILD.compiler_command()
        except RuntimeError as error:
            self.skipTest(str(error))
        probe = subprocess.run([*compiler, "-version"], capture_output=True, text=True)
        if probe.returncode:
            self.skipTest("System Java compiler module is unavailable")
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "DebianHttpAudit.java"
            source.write_text("public class DebianHttpAudit {\n"
                              "  public static void premain(String arg) {}\n"
                              "  static class Nested {}\n}\n")
            jar = Path(directory) / "agent.jar"
            BUILD.build(source, jar)
            first = jar.read_bytes()
            with zipfile.ZipFile(jar) as archive:
                self.assertEqual(archive.read(BUILD.SOURCE_HASH_ENTRY),
                                 hashlib.sha256(source.read_bytes()).hexdigest().encode("ascii"))
                self.assertEqual(len(archive.read(BUILD.SOURCE_HASH_ENTRY)), 64)
                self.assertIn(b"Premain-Class: DebianHttpAudit\r\n", archive.read("META-INF/MANIFEST.MF"))
                self.assertIn("DebianHttpAudit$Nested.class", archive.namelist())
                self.assertEqual(int.from_bytes(archive.read("DebianHttpAudit.class")[6:8], "big"), 55)
            java = shutil.which("java")
            if java:
                launched = subprocess.run([java, "-javaagent:" + str(jar), "-version"],
                                          capture_output=True, text=True)
                self.assertEqual(launched.returncode, 0, launched.stderr)
            BUILD.build(source, jar)
            self.assertEqual(jar.read_bytes(), first)


if __name__ == "__main__":
    unittest.main()
