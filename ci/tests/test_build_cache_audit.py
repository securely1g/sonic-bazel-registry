"""Preserve selected cache outcomes while keeping raw execution details private."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


SPEC = importlib.util.spec_from_file_location("registry_ci_audit", Path(__file__).resolve().parents[1] / "registry_ci.py")
ci = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ci)


class CacheAuditTests(unittest.TestCase):
    def test_extracts_named_spawns_and_declared_file_hashes(self):
        owner = "@@example+//:gen"
        file = {"path": "bazel-out/bin/gen/protoc", "digest": {"hash": "a" * 64}}
        spawn = {"targetLabel": owner, "mnemonic": "Gen", "runner": "remote cache hit",
                 "cacheHit": True, "exitCode": 0, "digest": {"hash": "b" * 64},
                 "listedOutputs": [file["path"], "bazel-out/bin/tree"],
                 "actualOutputs": [file, {"path": "bazel-out/bin/tree/child", "digest": {"hash": "c" * 64}}],
                 "environmentVariables": [{"name": "PRIVATE", "value": "private fixture"}]}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with ci.build_cache_audit([owner], root, root) as flags:
                raw = Path(flags[0].split("=", 1)[1])
                raw.write_text(json.dumps(spawn | {"targetLabel": "@@other+//:gen"}, indent=2) +
                               json.dumps(spawn, indent=2))
            log = root / "build-cache-audit.json"
            self.assertFalse(raw.exists())
            self.assertNotIn("private fixture", log.read_text())
            self.assertEqual(json.loads(log.read_text()), [{
                "targetLabel": owner, "mnemonic": "Gen", "runner": "remote cache hit",
                "cacheHit": True, "exitCode": 0, "actionDigest": "b" * 64,
                "outputs": [{"path": file["path"], "sha256": "a" * 64}],
            }])

    def test_absent_owner_fails_and_cleans_up(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaisesRegex(ci.RegistryError, "Missing cache audit targets"):
                with ci.build_cache_audit(["@@example+//:gen"], root, root) as flags:
                    raw = Path(flags[0].split("=", 1)[1])
                    raw.write_text("")
            self.assertFalse(raw.exists())
