"""Typed runtime provenance: actual files, admission and owner handoff."""
import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import container_provenance as provenance
import test_registry_ci as fixtures
registry_ci = fixtures.registry_ci


def root_stat(value):
    # Ordinary hosted unit jobs are unprivileged. Only ownership is simulated;
    # descriptors, symlinks, modes, sizes, replacement/races and helper execution
    # are real. The same cases also run as root for the independent UID fixture.
    fields = {name: getattr(value, name) for name in dir(value) if name.startswith("st_")}
    fields.update(st_uid=0, st_gid=0)
    return types.SimpleNamespace(**fields)


class Files:
    def __init__(self, root):
        self.root = root
        self.private = root / "private"
        self.private.mkdir(mode=0o700)
        self.work = self.private / "work"
        self.artifacts = root / "artifacts"
        self.artifacts.mkdir()
        self.marker = root / "marker.json"
        self.helpers = root / "helpers"
        self.helpers.mkdir(mode=0o755)
        self.fields = {"uid": 1000, "gid": 1000, "runner_root": "/opt/actions-runner",
                       "work_root": "/actions/_work", "base_image": "sha256:" + "a" * 64,
                       "base_image_ref": "unverified.example/base@sha256:" + "a" * 64,
                       "manager_revision": "b" * 40, "runner_version": "2.337.0"}
        self.put(self.marker, (json.dumps(self.fields) + "\n").encode(), 0o444)
        for name in provenance.HELPERS:
            self.put(self.helpers / name, b"raise AssertionError('must never execute helper')\n", 0o555)
        self.expected = self.private / "expected-provenance.json"

    @staticmethod
    def put(path, content, mode):
        if path.exists():
            path.chmod(0o600)
        path.write_bytes(content)
        path.chmod(mode)

    def install(self, test):
        test.enterContext(mock.patch.object(provenance, "MARKER", self.marker))
        test.enterContext(mock.patch.object(provenance, "HELPER_ROOT", self.helpers))
        test.enterContext(mock.patch.object(provenance, "require_container"))
        actual_fstat, actual_stat = os.fstat, os.stat
        test.enterContext(mock.patch.object(provenance.os, "fstat",
                          side_effect=lambda fd: root_stat(actual_fstat(fd))))
        test.enterContext(mock.patch.object(provenance.os, "stat",
                          side_effect=lambda *a, **k: root_stat(actual_stat(*a, **k))))
        self.identity = provenance.measure()
        self.put(self.expected, (json.dumps(self.identity) + "\n").encode(), 0o400)

    def session(self):
        return provenance.Session(self.expected, self.work, self.artifacts)


class IdentityTests(unittest.TestCase):
    def setUp(self):
        self.temp = self.enterContext(tempfile.TemporaryDirectory())
        self.files = Files(Path(self.temp))
        self.files.install(self)

    def test_exact_live_files_are_measured_without_executing_helpers(self):
        session = self.files.session()
        reference = session.check("before_build")
        self.assertTrue(reference.startswith(provenance.PREFIX))
        self.assertNotIn("@sha256:", reference)
        self.assertNotIn("base_image_ref", session.identity["marker"])
        session.check("before_preparation")
        session.check("after_preparation")
        session.finish(False)
        receipt = json.loads((self.files.artifacts / "test-container-provenance.json").read_text())
        self.assertEqual(receipt["status"], "passed")
        self.assertEqual(len(receipt["checks"]), 3)
        self.assertEqual((self.files.artifacts / "test-container-provenance.expected.json").read_bytes(),
                         self.files.expected.read_bytes())
        self.assertFalse(receipt["registry_manifest_digest_verified"])

    def test_schema_rejects_bool_integer_substitution_and_unknown_keys(self):
        cases = [("schema",), ("marker_file", "uid"), ("marker_file", "gid"),
                 ("marker_file", "mode"), ("marker_file", "bytes"), ("marker", "uid"),
                 ("marker", "gid"), ("installed_provisioner_helpers", "entrypoint.py", "uid")]
        for path in cases:
            value = copy.deepcopy(self.files.identity)
            target = value
            for part in path[:-1]:
                target = target[part]
            target[path[-1]] = False if target[path[-1]] == 0 else True
            with self.subTest(path=path), self.assertRaises(provenance.ProvenanceError):
                provenance.validate_identity(value)
        for path in ((), ("marker",), ("marker_file",), ("installed_provisioner_helpers",)):
            value = copy.deepcopy(self.files.identity)
            target = value
            for part in path:
                target = target[part]
            target["extra"] = "not allowed"
            with self.subTest(path=path), self.assertRaises(provenance.ProvenanceError):
                provenance.validate_identity(value)

    def test_json_duplicates_nonfinite_and_false_digest_claims_fail(self):
        for raw in (b'{"schema":1,"schema":1}', b'{"x":NaN}', b"\xff"):
            with self.subTest(raw=raw), self.assertRaises(provenance.ProvenanceError):
                provenance.parse(raw)
        for key in ("registry_manifest_digest_verified", "derived_image_digest_verified"):
            for value in (True, 0, "false"):
                identity = copy.deepcopy(self.files.identity); identity[key] = value
                with self.subTest(key=key, value=value), self.assertRaises(provenance.ProvenanceError):
                    provenance.validate_identity(identity)

    def test_live_marker_helper_and_expected_byte_drift_fail(self):
        for case in ("marker", "helper", "expected"):
            with self.subTest(case=case):
                session = self.files.session(); session.check("before_build")
                path = {"marker": self.files.marker, "helper": self.files.helpers / "entrypoint.py",
                        "expected": self.files.expected}[case]
                before = path.read_bytes(); mode = path.stat().st_mode & 0o777
                self.files.put(path, before + b" ", mode)
                with self.assertRaises(provenance.ProvenanceError):
                    session.check("before_preparation")
                receipt = json.loads((self.files.artifacts / "test-container-provenance.json").read_text())
                self.assertEqual(receipt["status"], "failed")
                self.assertEqual(receipt["failed_stage"], "before_preparation")
                self.files.put(path, before, mode)

    def test_expected_path_confinement_private_mode_and_symlink_fail(self):
        outside = self.files.root / "outside.json"
        self.files.put(outside, self.files.expected.read_bytes(), 0o400)
        for path in (outside, Path("expected-provenance.json"),
                     self.files.private / ".." / "private" / "expected-provenance.json"):
            with self.subTest(path=path), self.assertRaises(provenance.ProvenanceError):
                provenance.Session(path, self.files.work, self.files.artifacts).check("before_build")
        self.files.private.chmod(0o755)
        with self.assertRaises(provenance.ProvenanceError): self.files.session().check("before_build")
        self.files.private.chmod(0o700)
        self.files.expected.unlink(); self.files.expected.symlink_to(outside)
        with self.assertRaises(OSError): self.files.session().check("before_build")

    def test_fixed_files_reject_symlink_parent_fifo_size_modes_and_hardlinks(self):
        path = self.files.helpers / "entrypoint.py"; original = path.read_bytes()
        for mode in (0o755, 0o444, 0o777):
            path.chmod(mode)
            with self.subTest(mode=mode), self.assertRaises(provenance.ProvenanceError): provenance.measure()
        path.chmod(0o555)
        other = self.files.root / "other"; self.files.put(other, original, 0o555)
        path.unlink(); path.symlink_to(other)
        with self.assertRaises(OSError): provenance.measure()
        path.unlink(); os.mkfifo(path, 0o555)
        with self.assertRaises(provenance.ProvenanceError): provenance.measure()
        path.unlink(); os.link(other, path)
        with self.assertRaises(provenance.ProvenanceError): provenance.measure()
        path.unlink(); self.files.put(path, b"a" * (1024 * 1024 + 1), 0o555)
        with self.assertRaises(provenance.ProvenanceError): provenance.measure()
        self.files.put(path, original, 0o555)
        moved = self.files.root / "moved"
        self.files.helpers.rename(moved); self.files.helpers.symlink_to(moved)
        with self.assertRaises(OSError): provenance.measure()

    def test_metadata_uid_gid_and_read_race_are_rejected(self):
        actual = provenance.os.fstat
        for field in ("st_uid", "st_gid"):
            def changed(fd):
                value = actual(fd)
                if value.st_size == self.files.marker.stat().st_size:
                    setattr(value, field, 1000)
                return value
            with self.subTest(field=field), mock.patch.object(provenance.os, "fstat", side_effect=changed):
                with self.assertRaises(provenance.ProvenanceError): provenance.measure()
        calls = 0
        def raced(fd):
            nonlocal calls
            value = actual(fd)
            if value.st_size == self.files.marker.stat().st_size:
                calls += 1
                if calls == 2:
                    value.st_mtime_ns += 1
            return value
        with mock.patch.object(provenance.os, "fstat", side_effect=raced):
            with self.assertRaisesRegex(provenance.ProvenanceError, "changed"): provenance.measure()

    def test_replaced_parent_is_rejected_against_open_descriptor(self):
        original = provenance._directory
        calls = 0
        def replace(path):
            nonlocal calls
            if path == self.files.helpers:
                calls += 1
                if calls == 2:
                    old = self.files.root / "prior-helpers"
                    self.files.helpers.rename(old)
                    self.files.helpers.mkdir(mode=0o755)
                    for name in provenance.HELPERS:
                        self.files.put(self.files.helpers / name, (old / name).read_bytes(), 0o555)
            return original(path)
        with mock.patch.object(provenance, "_directory", side_effect=replace):
            with self.assertRaisesRegex(provenance.ProvenanceError, "parent changed"):
                provenance.measure()

    def test_symlinked_work_directory_is_rejected_before_admission(self):
        outside = self.files.root / "outside-work"; outside.mkdir()
        self.files.work.symlink_to(outside, target_is_directory=True)
        with self.assertRaises(provenance.ProvenanceError):
            self.files.session().check("before_build")

    def test_failure_receipt_excludes_private_error_text(self):
        with mock.patch.object(provenance, "measure", side_effect=OSError("secret-proxy-token")):
            with self.assertRaises(OSError): self.files.session().check("before_build")
        text = (self.files.artifacts / "test-container-provenance.json").read_text()
        self.assertNotIn("secret-proxy-token", text)
        self.assertEqual(json.loads(text)["error_class"], "OSError")


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.FetchedModuleTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.f = self.fixture
        self.f.runtime_fixture()
        root = self.f.root / "typed"; root.mkdir(mode=0o755)
        self.files = Files(root); self.files.install(self)

    def run_typed(self):
        return registry_ci.run(self.f.root, "alpha", "1.0.0", self.f.architecture,
                               self.files.work, self.files.artifacts, str(self.f.fake_bazel),
                               test_container_provenance=self.files.expected)

    def test_real_owner_fixture_receipt_and_full_test_arguments(self):
        with mock.patch.object(registry_ci, "run_logged", wraps=registry_ci.run_logged) as run:
            self.run_typed()
        commands = [call.args[0] for call in run.call_args_list]
        self.assertEqual(len(commands), 3)
        receipt = json.loads((self.files.artifacts / "test-runtime.json").read_text())
        ref = provenance.reference(self.files.identity)
        self.assertEqual(receipt["image_reference"], ref)
        flag = "--test_env=SONIC_TEST_RUNTIME_ID=" + receipt["SONIC_TEST_RUNTIME_ID"]
        self.assertNotIn(flag, commands[0]); self.assertIn(flag, commands[2])
        self.assertTrue(set(self.f.config["build_targets"]).issubset(commands[0]))
        self.assertTrue(set(self.f.config["test_targets"]).issubset(commands[2]))
        self.assertIn("--nocache_test_results", commands[2])
        result = json.loads((self.files.artifacts / "validation.json").read_text())
        self.assertEqual(result["test_container_provenance"]["reference"], ref)

    def test_rejection_before_build_and_neither_or_both_options(self):
        self.files.expected.chmod(0o600)
        with mock.patch.object(registry_ci, "run_logged") as run:
            with self.assertRaises(provenance.ProvenanceError): self.run_typed()
            run.assert_not_called()
        self.files.expected.chmod(0o400)
        with mock.patch.object(registry_ci, "run_logged") as run:
            with self.assertRaises(registry_ci.RegistryError):
                registry_ci.run(self.f.root, "alpha", "1.0.0", self.f.architecture,
                                self.files.work, self.files.artifacts, str(self.f.fake_bazel),
                                "example@sha256:" + "a" * 64, self.files.expected)
            run.assert_not_called()
        with mock.patch.object(registry_ci, "run_logged") as run:
            with self.assertRaises(registry_ci.RegistryError):
                registry_ci.run(self.f.root, "alpha", "1.0.0", self.f.architecture,
                                self.files.work, self.files.artifacts, str(self.f.fake_bazel))
            run.assert_not_called()

    def test_profile_without_runtime_hook_rejects_typed_mode(self):
        del self.f.config["test_runtime_preparation"]
        self.f.config_path.write_text(json.dumps(self.f.config))
        with mock.patch.object(registry_ci, "run_logged") as run:
            with self.assertRaisesRegex(registry_ci.RegistryError, "source-owned"): self.run_typed()
            run.assert_not_called()

    def test_before_preparation_live_drift_stops_helper_and_tests(self):
        actual = registry_ci.run_logged
        def drift(command, cwd, log):
            actual(command, cwd, log)
            if log.name == "build.log":
                self.files.put(self.files.marker, self.files.marker.read_bytes() + b" ", 0o444)
        with mock.patch.object(registry_ci, "run_logged", side_effect=drift) as run:
            with self.assertRaises(provenance.ProvenanceError): self.run_typed()
        self.assertEqual(len(run.call_args_list), 1)

    def test_after_preparation_live_drift_stops_tests(self):
        actual = registry_ci.run_logged
        def drift(command, cwd, log):
            actual(command, cwd, log)
            if log.name == "test-runtime-preparation.log":
                self.files.put(self.files.helpers / "entrypoint.py", b"changed", 0o555)
        with mock.patch.object(registry_ci, "run_logged", side_effect=drift) as run:
            with self.assertRaises(provenance.ProvenanceError): self.run_typed()
        self.assertEqual(len(run.call_args_list), 2)
        self.assertTrue((self.files.artifacts / "test-runtime.json").exists())
        side = json.loads((self.files.artifacts / "test-container-provenance.json").read_text())
        self.assertEqual(side["failed_stage"], "after_preparation")

    def test_owner_failure_retains_sidecar_and_original_helper_log(self):
        actual = registry_ci.run_logged
        def fail(command, cwd, log):
            actual(command, cwd, log)
            if log.name == "test-runtime-preparation.log":
                raise registry_ci.RegistryError("owner failed")
        with mock.patch.object(registry_ci, "run_logged", side_effect=fail) as run:
            with self.assertRaises(registry_ci.RegistryError): self.run_typed()
        self.assertEqual(len(run.call_args_list), 2)
        side = json.loads((self.files.artifacts / "test-container-provenance.json").read_text())
        self.assertEqual(side["status"], "failed")
        self.assertEqual(side["checks"][-1]["stage"], "after_preparation")

    def test_typed_owner_receipt_hash_lock_architecture_and_reference_tampering(self):
        actual = registry_ci.run_logged
        other_architecture = "arm64" if self.f.architecture == "amd64" else "amd64"
        for field, value in (("architecture", other_architecture), ("image_reference", "wrong"),
                             ("lock_sha256", "wrong"), ("SONIC_TEST_RUNTIME_ID", "c" * 64)):
            artifacts = self.files.artifacts / field; artifacts.mkdir()
            work = self.files.private / ("work-" + field)
            def corrupt(command, cwd, log):
                actual(command, cwd, log)
                if log.name == "test-runtime-preparation.log":
                    path = log.parent / "test-runtime.json"
                    receipt = json.loads(path.read_text()); receipt[field] = value
                    path.write_text(json.dumps(receipt))
            with self.subTest(field=field), mock.patch.object(registry_ci, "run_logged", side_effect=corrupt) as run:
                with self.assertRaises(registry_ci.RegistryError):
                    registry_ci.run(self.f.root, "alpha", "1.0.0", self.f.architecture,
                                    work, artifacts, str(self.f.fake_bazel),
                                    test_container_provenance=self.files.expected)
                self.assertEqual(len(run.call_args_list), 2)
                self.assertEqual(json.loads((artifacts / "test-container-provenance.json").read_text())["status"],
                                 "failed")

    def test_typed_helper_checksum_still_rejects_before_execution(self):
        helper = self.f.fetched.parent / self.f.config["test_runtime_preparation"]["script"]
        helper.write_text(helper.read_text() + "# altered\\n")
        with mock.patch.object(registry_ci, "run_logged", wraps=registry_ci.run_logged) as run:
            with self.assertRaisesRegex(registry_ci.RegistryError, "checksum"): self.run_typed()
            self.assertEqual(len(run.call_args_list), 1)

    def test_cli_rejects_both_options(self):
        argv = ["registry_ci.py", "run", "--module", "alpha", "--version", "1.0.0",
                "--architecture", "amd64", "--work-dir", str(self.files.work),
                "--artifacts", str(self.files.artifacts), "--test-container-image",
                "example@sha256:" + "a" * 64, "--test-container-provenance", str(self.files.expected)]
        with mock.patch.object(sys, "argv", argv), self.assertRaises(SystemExit):
            registry_ci.main()


class ContainerGuardTests(unittest.TestCase):
    def test_root_container_trixie_and_native_amd64_are_all_required(self):
        cases = [(0, True, "ID=debian\nVERSION_CODENAME=trixie\n", "Linux", "x86_64", True),
                 (1000, True, "ID=debian\nVERSION_CODENAME=trixie\n", "Linux", "x86_64", False),
                 (0, False, "ID=debian\nVERSION_CODENAME=trixie\n", "Linux", "x86_64", False),
                 (0, True, "ID=ubuntu\nVERSION_CODENAME=trixie\n", "Linux", "x86_64", False),
                 (0, True, "ID=debian\nVERSION_CODENAME=bookworm\n", "Linux", "x86_64", False),
                 (0, True, "ID=debian\nVERSION_CODENAME=trixie\n", "Linux", "aarch64", False)]
        for uid, container, release, system, machine, accepted in cases:
            with self.subTest(uid=uid, container=container, release=release, machine=machine), \
                 mock.patch.object(provenance.os, "geteuid", return_value=uid), \
                 mock.patch.object(provenance.Path, "exists", return_value=container), \
                 mock.patch.object(provenance.Path, "read_text", return_value=release), \
                 mock.patch.object(provenance.platform, "system", return_value=system), \
                 mock.patch.object(provenance.platform, "machine", return_value=machine):
                if accepted:
                    provenance.require_container()
                else:
                    with self.assertRaises(provenance.ProvenanceError): provenance.require_container()

if __name__ == "__main__":
    unittest.main()
