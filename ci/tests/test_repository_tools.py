"""Repository evaluation must recognize linker scripts before trying readelf."""

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "prepare_repository_tools.sh"
STUB = r'''
import json
import os
from pathlib import Path
import sys

root = Path(os.environ["FIXTURE_ROOT"])
name = Path(sys.argv[0]).name
args = sys.argv[1:]
with (root / "commands.jsonl").open("a") as log:
    log.write(json.dumps([name, *args]) + "\n")
if name == "id":
    assert args == ["-u"]
    print(os.environ["FIXTURE_UID"])
elif name == "sudo":
    assert args[0] == "-n"
    status = int(os.environ.get("SUDO_STATUS", "0"))
    if status:
        sys.exit(status)
    os.execvpe(args[1], args[1:], os.environ)
elif name == "apt-get":
    if args == ["-o", "APT::Update::Error-Mode=any", "update"]:
        sys.exit(int(os.environ.get("UPDATE_STATUS", "0")))
    assert args == ["install", "-y", "--no-install-recommends", "file"]
    status = int(os.environ.get("INSTALL_STATUS", "0"))
    if status:
        sys.exit(status)
    (root / "bin/file").symlink_to("stub")
elif name == "file":
    if args == ["--version"]:
        print("file-fixture")
    else:
        assert args == ["--mime-type", "-b", "-"]
        assert sys.stdin.read() == "INPUT(libncursesw.so.6 -ltinfo)\n"
        print(os.environ.get("MIME_TYPE", "text/plain"))
        sys.exit(int(os.environ.get("FILE_STATUS", "0")))
else:
    raise AssertionError(name)
'''


class RepositoryToolsTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="repository tools ")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        stub = self.bin / "stub"
        stub.write_text("#!" + sys.executable + "\n" + STUB)
        stub.chmod(0o755)
        for name in ("id", "sudo", "apt-get"):
            (self.bin / name).symlink_to("stub")

    def run_helper(self, *, present=True, real=False, **environment):
        if present:
            tool = self.bin / "file"
            tool.unlink(missing_ok=True)
            if real:
                executable = shutil.which("file")
                self.assertIsNotNone(executable, "CI must prepare file before its tests")
                tool.symlink_to(executable)
            else:
                tool.symlink_to("stub")
        return subprocess.run(
            ["/bin/bash", str(SCRIPT)], cwd=self.root,
            env={"PATH": str(self.bin), "FIXTURE_ROOT": str(self.root),
                 "FIXTURE_UID": "1000", **environment},
            text=True, capture_output=True,
        )

    def commands(self):
        log = self.root / "commands.jsonl"
        return [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []

    def test_preinstalled_tool_is_validated_without_privileges_or_network(self):
        """A healthy image needs only MIME/version checks, never sudo or APT."""
        result = self.run_helper()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.commands(), [["file", "--mime-type", "-b", "-"], ["file", "--version"]])

    def test_missing_tool_is_installed_before_use_for_root_and_nonroot(self):
        """Both hosted containers and non-root workers prepare the same package."""
        for uid in ("0", "1000"):
            with self.subTest(uid=uid):
                (self.bin / "file").unlink(missing_ok=True)
                (self.root / "commands.jsonl").unlink(missing_ok=True)
                result = self.run_helper(present=False, FIXTURE_UID=uid)
                self.assertEqual(result.returncode, 0, result.stderr)
                commands = self.commands()
                apt = [row for row in commands if row[0] == "apt-get"]
                self.assertEqual(apt, [
                    ["apt-get", "-o", "APT::Update::Error-Mode=any", "update"],
                    ["apt-get", "install", "-y", "--no-install-recommends", "file"],
                ])
                self.assertEqual(sum(row[0] == "sudo" for row in commands), 0 if uid == "0" else 2)
                self.assertGreater(commands.index(["file", "--mime-type", "-b", "-"]), commands.index(apt[-1]))

    def test_preparation_failures_cannot_reach_repository_tool_validation(self):
        """Failed privilege checks, index refreshes or installs cannot pass CI."""
        for setting in ("SUDO_STATUS", "UPDATE_STATUS", "INSTALL_STATUS"):
            with self.subTest(setting=setting):
                (self.root / "commands.jsonl").unlink(missing_ok=True)
                result = self.run_helper(present=False, **{setting: "31"})
                self.assertEqual(result.returncode, 31, result.stderr)
                self.assertFalse((self.bin / "file").exists())
                self.assertFalse(any(row[0] == "file" for row in self.commands()))
                if setting != "INSTALL_STATUS":
                    self.assertFalse(any(row[:2] == ["apt-get", "install"] for row in self.commands()))

    def test_broken_magic_or_nontext_classification_fails_before_bazel(self):
        """An executable alone is insufficient when its magic data is unusable."""
        for environment in ({"FILE_STATUS": "1"}, {"MIME_TYPE": "application/octet-stream"}, {"MIME_TYPE": ""}):
            with self.subTest(environment=environment):
                (self.root / "commands.jsonl").unlink(missing_ok=True)
                result = self.run_helper(**environment)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("linker script", result.stderr)
                self.assertEqual(self.commands(), [["file", "--mime-type", "-b", "-"]])

    def test_real_file_and_magic_recognize_the_ncurses_linker_script(self):
        """Exercise the real classifier and installed magic database, not a stub."""
        result = self.run_helper(real=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("file-", result.stdout)
        self.assertEqual(self.commands(), [])


if __name__ == "__main__":
    unittest.main()
