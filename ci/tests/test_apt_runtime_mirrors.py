import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


SPEC = importlib.util.spec_from_file_location("apt_runtime_mirrors", Path(__file__).parents[1] / "apt_runtime_mirrors.py")
mirrors = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mirrors)
sys.path.insert(0, str(Path(__file__).parents[1]))
import registry_ci
SOURCE = "https://snapshot.debian.org/archive/debian/20260727T143429Z"
PRIVATE = "https://mirror.example.invalid/debian/20260727T143429Z"


class AptRuntimeMirrorsTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.config = self.root / "mirrors.json"
        self.config.write_text(json.dumps({"schema_version": 1, "mirrors": {SOURCE: PRIVATE}}))
        self.payload = b"a selected package payload"
        self.selected = {"libexample1": {
            "name": "libexample1", "version": "1.0-1", "architecture": "amd64", "suite": "trixie",
            "sha256": hashlib.sha256(self.payload).hexdigest(),
            "urls": [SOURCE + "/pool/main/e/example/libexample1_1.0-1_amd64.deb"],
        }}
        self.requested = ["libexample1:amd64=1.0-1"]

    def owner(self, before, after):
        return {"select_runtime": mock.Mock(return_value=self.selected),
                "snapshot_sources": mock.Mock(), "inventory": mock.Mock(side_effect=[before, after]),
                "missing_packages": lambda selected, installed: [f"{name}:{p['architecture']}={p['version']}"
                    for name, p in selected.items() if f"{name}:{p['architecture']}" not in installed],
                "verify_inventory": mock.Mock()}

    def test_private_priority_and_per_file_public_fallback_use_native_transport(self):
        result = mirrors.write_sources(self.root, self.selected, "amd64", mirrors.read_mirrors(self.config))
        source = (self.root / "sources.list").read_text()
        self.assertIn("mirror+file:///", source)
        self.assertNotIn(PRIVATE, source)
        listing, = self.root.glob("*.mirrors")
        self.assertEqual(listing.stat().st_mode & 0o777, 0o400)
        self.assertEqual(listing.read_text(), PRIVATE + "/\tpriority:1\n" + SOURCE + "/\tpriority:2\n")
        self.assertEqual(result, {"mapped_snapshots": [SOURCE], "unmapped_snapshots": []})
        self.assertNotIn(PRIVATE, json.dumps(result))

    def test_unmapped_snapshots_keep_public_source_and_are_reported(self):
        result = mirrors.write_sources(self.root, self.selected, "amd64", {})
        self.assertIn(SOURCE, (self.root / "sources.list").read_text())
        self.assertEqual(result["unmapped_snapshots"], [SOURCE])

    def test_reject_unsafe_or_unrelated_mappings_without_echoing_them(self):
        for source, target in [("https://deb.debian.org/debian", PRIVATE),
                               (SOURCE, "http://mirror.example.invalid/debian"),
                               (SOURCE, PRIVATE + "\ntrusted=yes"),
                               (SOURCE, "https://user:secret@mirror.example.invalid/debian"),
                               (SOURCE, PRIVATE + "?secret=token")]:
            with self.subTest(source=source, target=target):
                self.config.write_text(json.dumps({"schema_version": 1, "mirrors": {source: target}}))
                with self.assertRaises(ValueError) as caught:
                    mirrors.read_mirrors(self.config)
                self.assertNotIn(target, str(caught.exception))

    def test_source_hash_is_checked_before_loading_the_owner(self):
        script = self.root / "owner.py"
        marker = self.root / "executed"
        script.write_text(f"from pathlib import Path\nPath({str(marker)!r}).touch()\n")
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            mirrors.load_owner(script, "0" * 64)
        self.assertFalse(marker.exists())

    def test_verified_owner_must_explicitly_implement_the_protocol(self):
        script = self.root / "owner.py"
        script.write_text("pass\n")
        with self.assertRaisesRegex(ValueError, "preparation protocol"):
            mirrors.load_owner(script, hashlib.sha256(script.read_bytes()).hexdigest())

    def test_archive_verification_requires_the_complete_exact_selected_set(self):
        archive = self.root / "package.deb"
        archive.write_bytes(self.payload)
        metadata = "Package: libexample1\nVersion: 1.0-1\nArchitecture: amd64\n"
        with mock.patch.object(mirrors.subprocess, "check_output", return_value=metadata):
            verified = mirrors.verify_archives(self.root, self.selected, self.requested)
            self.assertEqual(verified[0]["sha256"], self.selected["libexample1"]["sha256"])
            archive.write_bytes(b"corrupt")
            with self.assertRaisesRegex(ValueError, "unselected"):
                mirrors.verify_archives(self.root, self.selected, self.requested)
            archive.unlink()
            with self.assertRaisesRegex(ValueError, "complete selected"):
                mirrors.verify_archives(self.root, self.selected, self.requested)

    def test_preinstalled_runtime_runs_owner_checks_without_any_apt(self):
        before = {"libexample1:amd64": "1.0-1"}
        owner = self.owner(before, before)
        lock = self.root / "lock.json"
        lock.write_text("{}")
        with mock.patch.object(mirrors.subprocess, "run") as run:
            result = mirrors.prepare(owner, lock, self.config, self.root / "apt.log", self.root / "result.json", "amd64")
        run.assert_not_called()
        owner["snapshot_sources"].assert_called_once_with(self.selected, "amd64")
        owner["verify_inventory"].assert_called_once_with(self.selected, before, before)
        self.assertEqual(result["result"], "passed")
        self.assertEqual(result["verified_downloads"], [])

    def test_checks_downloads_before_offline_install_and_preserves_base_inventory(self):
        before, after = {"libc6:amd64": "2.41"}, {"libc6:amd64": "2.41", "libexample1:amd64": "1.0-1"}
        owner = self.owner(before, after)
        lock = self.root / "lock.json"
        lock.write_text("{}")
        commands = []

        def run(command, **kwargs):
            commands.append(command)
            if "--download-only" in command:
                archives = Path(next(arg.split("=", 1)[1] for arg in command if arg.startswith("Dir::Cache::archives=")))
                (archives / "package.deb").write_bytes(self.payload)
            return subprocess.CompletedProcess(command, 0)

        def output(command, **kwargs):
            if command[0] == "dpkg-deb":
                return "Package: libexample1\nVersion: 1.0-1\nArchitecture: amd64\n"
            return "Inst libexample1 (1.0-1 fixture [amd64])\n"

        with mock.patch.object(mirrors.subprocess, "run", side_effect=run), \
                mock.patch.object(mirrors.subprocess, "check_output", side_effect=output):
            result = mirrors.prepare(owner, lock, self.config, self.root / "apt.log", self.root / "result.json", "amd64")
        owner["verify_inventory"].assert_called_once_with(self.selected, before, after)
        self.assertEqual(len(result["verified_downloads"]), 1)
        self.assertTrue(any("--no-download" in command for command in commands))
        self.assertTrue(all("--allow-unauthenticated" not in command for command in commands))
        self.assertNotIn(PRIVATE, json.dumps(result))

    def test_rejects_planned_base_upgrade_before_downloading(self):
        owner = self.owner({"libc6:amd64": "2.41"}, {})
        lock = self.root / "lock.json"
        lock.write_text("{}")
        with mock.patch.object(mirrors.subprocess, "run") as run, \
                mock.patch.object(mirrors.subprocess, "check_output", return_value="Inst libc6 [2.41] (2.42 fixture [amd64])\n"):
            with self.assertRaisesRegex(ValueError, "prepared-base"):
                mirrors.prepare(owner, lock, self.config, self.root / "apt.log", self.root / "result.json", "amd64")
        self.assertFalse(any("--download-only" in call.args[0] for call in run.call_args_list))
        self.assertEqual(json.loads((self.root / "result.json").read_text())["result"], "incomplete")

    def test_registry_hook_keeps_owner_bytes_and_uses_the_same_arm_guest(self):
        source = self.root / "source"
        source.mkdir()
        helper = source / "prepare.py"
        helper.write_text("# verified source helper\n")
        sha = hashlib.sha256(helper.read_bytes()).hexdigest()
        consumer = self.root / "consumer"
        consumer.mkdir()
        lock = consumer / "MODULE.bazel.lock"
        lock.write_text("{}")
        artifacts = self.root / "artifacts"
        artifacts.mkdir()
        prefix = ["/guest-executor", "--bind", str(consumer), "--bind", str(artifacts), "--"]
        original_prefix = list(prefix)
        image = "debian:trixie@sha256:" + "b" * 64
        calls = []

        def execute(command, cwd, log):
            calls.append(command)
            if str(helper) in command and "--owner-script" not in command:
                receipt = {"architecture": "arm64", "image_reference": image,
                           "lock_sha256": hashlib.sha256(lock.read_bytes()).hexdigest(),
                           "preserved_base_packages": {}, "runtime_libraries": {}}
                identity = {k: v for k, v in receipt.items()
                            if k not in ("preserved_base_packages", "lock_sha256")}
                receipt["SONIC_TEST_RUNTIME_ID"] = hashlib.sha256(json.dumps(
                    identity, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
                (artifacts / "test-runtime.json").write_text(json.dumps(receipt))

        with mock.patch.dict(mirrors.os.environ, {"SONIC_APT_MIRROR_CONFIG": str(self.config)}), \
                mock.patch.object(registry_ci, "require_test_container"), \
                mock.patch.object(registry_ci, "run_logged", side_effect=execute):
            registry_ci.prepare_test_runtime({"test_runtime_preparation": {"script": "prepare.py", "sha256": sha,
                                                                          "apt_mirror_protocol": "locked-runtime-v1"}},
                                             source, consumer, artifacts, "arm64", image, prefix)
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0][:len(prefix) - 1], prefix[:-1])
        self.assertIn(str(self.config), calls[0][:calls[0].index("--")])
        self.assertIn(str(Path(registry_ci.__file__).parent), calls[0][:calls[0].index("--")])
        self.assertEqual(calls[0][calls[0].index("--") + 1], "/usr/bin/python3")
        self.assertEqual(calls[1][:len(prefix)], prefix)
        self.assertNotIn("--mirror-config", calls[1])
        self.assertEqual(prefix, original_prefix)
        self.assertEqual(hashlib.sha256(helper.read_bytes()).hexdigest(), sha)
        calls.clear()
        with mock.patch.dict(mirrors.os.environ, {"SONIC_APT_MIRROR_CONFIG": str(self.root / "absent-map")}), \
                mock.patch.object(registry_ci, "require_test_container"), \
                mock.patch.object(registry_ci, "run_logged", side_effect=execute):
            registry_ci.prepare_test_runtime({"test_runtime_preparation": {"script": "prepare.py", "sha256": sha}},
                                             source, consumer, artifacts, "arm64", image, prefix)
        self.assertEqual(len(calls), 1, "An owner without the explicit protocol must keep its original path")
        self.assertIn(str(helper), calls[0])


if __name__ == "__main__":
    unittest.main()
