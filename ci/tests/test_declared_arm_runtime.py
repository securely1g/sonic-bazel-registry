import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest


EXECUTOR = Path(__file__).resolve().parents[1] / "declared_arm_runtime.py"


class DeclaredArmRuntimeTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        for name in ("original", "suite/wrapper", "unrelated/wrapper"):
            script = self.root / name
            script.parent.mkdir(parents=True, exist_ok=True)
            script.write_text('#!/bin/sh\nprintf "%s\\n" "$0" "$@"\n')
            script.chmod(0o755)
        (self.root / "_main").mkdir()
        self.payload = self.root / "module+" / "payload"
        self.payload.parent.mkdir()
        self.environment = {**os.environ, "TEST_SRCDIR": str(self.root), "TEST_WORKSPACE": "_main"}
        self.original = [str(self.root / "original"), "--bind-at", "/host path", "/guest path", "--"]

    def invoke(self, wrapper):
        return subprocess.run([
            EXECUTOR, json.dumps({"suite/wrapper": "module+/payload"}),
            *self.original, str(self.root / wrapper), "test argument",
        ], env=self.environment, text=True, capture_output=True)

    def test_selected_wrapper_receives_original_arguments(self):
        self.payload.write_bytes(b"\x7fELF\x02\x01" + bytes(12) + struct.pack("<H", 183))
        result = self.invoke("suite/wrapper")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), [str(self.root / "suite/wrapper"), "test argument"])
        self.assertIn("binfmt with AArch64 module+/payload", result.stderr)

    def test_selected_wrapper_rejects_a_native_payload(self):
        self.payload.write_bytes(b"\x7fELF\x02\x01" + bytes(12) + struct.pack("<H", 62))
        result = self.invoke("suite/wrapper")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Expected a declared", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_other_wrappers_keep_the_entire_original_executor(self):
        result = self.invoke("unrelated/wrapper")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), [
            *self.original, str(self.root / "unrelated/wrapper"), "test argument",
        ])
