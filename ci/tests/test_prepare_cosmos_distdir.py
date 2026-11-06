"""Exercise verified distdir publication without network or native execution."""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import textwrap
import unittest
from unittest import mock
import warnings
import zipfile


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("cosmos_distdir", ROOT / "ci/prepare_cosmos_distdir.py")
assert SPEC is not None and SPEC.loader is not None
cosmos = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cosmos)


class CosmosDistdirTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.distdir, self.cache = self.root / "distdir", self.root / "cache"
        self.receipt = self.root / "artifacts" / "cosmos.json"
        self.payloads = {"assimilate": b"fixture assimilator", "ape-x86_64.elf": b"fixture loader",
                         "gzip.ape": b"fixture compressor"}
        self.pins = {name: (len(data), hashlib.sha256(data).hexdigest())
                     for name, data in self.payloads.items()}
        self.addCleanup(mock.patch.stopall)
        mock.patch.object(cosmos, "MEMBERS", self.pins).start()

    def zip_bytes(self, bad=None, bad_member="ape-x86_64.elf"):
        result = io.BytesIO()
        with zipfile.ZipFile(result, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, data in self.payloads.items():
                if bad == "missing" and name == bad_member:
                    continue
                info = zipfile.ZipInfo("bin/" + name)
                info.external_attr = (stat.S_IFREG | 0o755) << 16
                if bad == "symlink" and name == bad_member:
                    info.external_attr = (stat.S_IFLNK | 0o777) << 16
                if bad == "checksum" and name == bad_member:
                    data = b"X" * len(data)
                archive.writestr(info, data)
                if bad == "duplicate" and name == bad_member:
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore", UserWarning)
                        archive.writestr(info, data)
            archive.writestr("../../must-not-extract", b"ignored")
        return result.getvalue()

    @contextlib.contextmanager
    def download(self, data, length=True, status=200):
        response = io.BytesIO(data)
        response.status = status
        response.headers = {"Content-Length": str(len(data))} if length else {}
        with mock.patch.object(cosmos, "urlopen", return_value=response) as fetch:
            yield fetch

    def prepare(self, repository_cache=None):
        return cosmos.prepare(self.distdir, self.cache, self.receipt, repository_cache)

    def assert_published(self):
        self.assertEqual({path.name for path in self.distdir.iterdir()}, set(self.payloads))
        for name, data in self.payloads.items():
            self.assertEqual((self.distdir / name).read_bytes(), data)
            self.assertEqual(stat.S_IMODE((self.distdir / name).stat().st_mode), 0o644)
        self.assertFalse((self.root / "must-not-extract").exists())

    def test_official_zip_then_verified_distdir_hit_without_network(self):
        data = self.zip_bytes()
        with mock.patch.object(cosmos, "ARCHIVE_BYTES", len(data)), self.download(data) as fetch:
            result = self.prepare()
        fetch.assert_called_once_with(cosmos.ARCHIVE_URL, timeout=60)
        self.assert_published()
        self.assertFalse(result["whole_archive_digest_verified"])
        self.assertEqual({item["source"] for item in result["members"]}, {"official-release-zip"})
        self.assertEqual(json.loads(self.receipt.read_text()), result)
        self.assertEqual((self.cache / "cosmos-4.0.2.zip").read_bytes(), data)
        with mock.patch.object(cosmos, "urlopen", side_effect=AssertionError("unexpected network")):
            result = self.prepare()
        self.assertEqual({item["source"] for item in result["members"]}, {"distdir"})

    def test_verified_repository_cache_hit(self):
        repository = self.root / "repository"
        for name, data in self.payloads.items():
            path = repository / "content_addressable/sha256" / self.pins[name][1] / "file"
            path.parent.mkdir(parents=True)
            path.write_bytes(data)
        with mock.patch.object(cosmos, "urlopen", side_effect=AssertionError("unexpected network")):
            result = self.prepare(repository)
        self.assert_published()
        self.assertEqual({item["source"] for item in result["members"]}, {"repository-cache"})

    def test_cached_zip_is_verified_before_reuse(self):
        data = self.zip_bytes()
        self.cache.mkdir()
        (self.cache / "cosmos-4.0.2.zip").write_bytes(data)
        with mock.patch.object(cosmos, "ARCHIVE_BYTES", len(data)), mock.patch.object(
                cosmos, "urlopen", side_effect=AssertionError("unexpected network")):
            result = self.prepare()
        self.assert_published()
        self.assertEqual({item["source"] for item in result["members"]}, {"cached-release-zip"})

    def test_bad_second_member_does_not_publish_first_or_replace_old_files(self):
        self.distdir.mkdir()
        old = self.distdir / "assimilate"
        old.write_bytes(b"old invalid input")
        for bad in ("checksum", "missing", "duplicate", "symlink"):
            with self.subTest(bad=bad):
                data = self.zip_bytes(bad)
                with mock.patch.object(cosmos, "ARCHIVE_BYTES", len(data)), self.download(data):
                    with self.assertRaises(ValueError):
                        self.prepare()
                self.assertEqual(old.read_bytes(), b"old invalid input")
                self.assertFalse((self.distdir / "ape-x86_64.elf").exists())
                self.assertFalse(self.receipt.exists())
                self.assertEqual(list(self.cache.iterdir()), [])

    def test_download_rejects_wrong_status_length_truncation_and_oversize(self):
        data = self.zip_bytes()
        cases = ((data, True, 206), (data + b"extra", True, 200),
                 (data[:-1], False, 200), (data + b"extra", False, 200))
        for body, length, status in cases:
            with self.subTest(length=length, status=status, bytes=len(body)):
                with mock.patch.object(cosmos, "ARCHIVE_BYTES", len(data)), self.download(body, length, status):
                    with self.assertRaises(ValueError):
                        self.prepare()
                self.assertFalse(self.distdir.exists())
                self.assertFalse(self.receipt.exists())
                self.assertEqual(list(self.cache.iterdir()), [])

    def test_bad_gzip_in_cached_zip_preserves_existing_verified_inputs(self):
        self.distdir.mkdir()
        for name in ("assimilate", "ape-x86_64.elf"):
            (self.distdir / name).write_bytes(self.payloads[name])
        self.cache.mkdir()
        for bad in ("checksum", "missing", "duplicate", "symlink"):
            with self.subTest(bad=bad):
                data = self.zip_bytes(bad, "gzip.ape")
                (self.cache / "cosmos-4.0.2.zip").write_bytes(data)
                with mock.patch.object(cosmos, "ARCHIVE_BYTES", len(data)), mock.patch.object(
                        cosmos, "urlopen", side_effect=AssertionError("unexpected network")):
                    with self.assertRaises(ValueError):
                        self.prepare()
                self.assertEqual({path.name for path in self.distdir.iterdir()},
                                 {"assimilate", "ape-x86_64.elf"})
                for name in ("assimilate", "ape-x86_64.elf"):
                    self.assertEqual((self.distdir / name).read_bytes(), self.payloads[name])
                self.assertFalse(self.receipt.exists())

    def test_crc_damage_and_invalid_cached_zip_fail_without_publication(self):
        data = bytearray(self.zip_bytes())
        index = data.index(self.payloads["ape-x86_64.elf"])
        data[index] ^= 1
        self.cache.mkdir()
        (self.cache / "cosmos-4.0.2.zip").write_bytes(data)
        with mock.patch.object(cosmos, "ARCHIVE_BYTES", len(data)), mock.patch.object(
                cosmos, "urlopen", side_effect=AssertionError("unexpected network")):
            with self.assertRaises(zipfile.BadZipFile):
                self.prepare()
        self.assertFalse(self.distdir.exists())
        self.assertFalse(self.receipt.exists())

    def test_download_deadline_removes_incomplete_file(self):
        data = self.zip_bytes()
        with mock.patch.object(cosmos, "ARCHIVE_BYTES", len(data)), self.download(data), mock.patch.object(
                cosmos.time, "monotonic", side_effect=[0, 901]):
            with self.assertRaises(TimeoutError):
                self.prepare()
        self.assertEqual(list(self.cache.iterdir()), [])
        self.assertFalse(self.distdir.exists())


class CosmosWorkflowTest(unittest.TestCase):
    def test_actual_build_step_limits_opt_in_and_forwards_distdir(self):
        text = (ROOT / ".github/workflows/registry-module.yml").read_text()
        block = text.split("      - name: Build and test through the registry\n", 1)[1]
        block = textwrap.dedent(block.split("        run: |\n", 1)[1].split("      - name:", 1)[0])
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            recorder = root / "python3"
            recorder.write_text("#!/usr/bin/python3\nimport json, os, sys\n"
                                "with open(os.environ['CALLS'], 'a') as f: f.write(json.dumps(sys.argv[1:]) + '\\n')\n")
            (root / "sudo").write_text('#!/bin/sh\n[ "$1" = -n ] || exit 1\nshift\ncase "$1" in --preserve-env=*) shift;; esac\nexec "$@"\n')
            (root / "git").write_text("#!/bin/sh\nexit 0\n")
            for name in ("python3", "sudo", "git"):
                (root / name).chmod(0o755)
            cases = (("amd64", "amd64", False, "libteam", "1.31.0.sonic.1", True),
                     ("arm64", "arm64", False, "libteam", "1.31.0.sonic.1", False),
                     ("arm64", "amd64", True, "libteam", "1.31.0.sonic.1", False),
                     ("amd64", "amd64", False, "other", "1.31.0.sonic.1", False),
                     ("amd64", "amd64", False, "libteam", "1.31.0.sonic.2", False))
            for arch, execution, cross, module, version, enabled in cases:
                with self.subTest(arch=arch, execution=execution, cross=cross, module=module, version=version):
                    calls_path = root / "calls.jsonl"
                    calls_path.unlink(missing_ok=True)
                    env = {**os.environ, "PATH": str(root) + os.pathsep + os.environ["PATH"],
                           "CALLS": str(calls_path), "CI_ARCHITECTURE": arch,
                           "CI_EXECUTION_ARCHITECTURE": execution, "CI_CROSS_COMPILE": str(cross).lower(),
                           "ARM_TEST_EXECUTOR": str(root / "arm-executor"), "CI_MODULE": module,
                           "CI_VERSION": version, "RUNNER_TEMP": str(root / "temp with spaces"),
                           "GITHUB_WORKSPACE": str(root / "workspace"), "TEST_CONTAINER_IMAGE": "fixture-image",
                           "SONIC_RUNNER_IMAGE_REFERENCE": "fixture-image"}
                    subprocess.run(["bash", "-c", block], env=env, check=True, capture_output=True)
                    calls = [json.loads(line) for line in calls_path.read_text().splitlines()]
                    self.assertEqual(len(calls), 2 if enabled else 1)
                    self.assertEqual(calls[-1][:2], ["ci/private_mirrors.py", "run"])
                    command = calls[-1][calls[-1].index("--") + 1:]
                    self.assertEqual(command[:3], ["python3", "ci/registry_ci.py", "run"])
                    self.assertEqual("--cross-compile" in calls[-1], cross)
                    flags = [arg for arg in calls[-1] if arg.startswith("--bazel-build-arg=--distdir=")]
                    self.assertEqual(bool(flags), enabled)
                    if enabled:
                        self.assertEqual(calls[0][0], "ci/prepare_cosmos_distdir.py")
                        distdir = calls[0][calls[0].index("--distdir") + 1]
                        self.assertEqual(flags, ["--bazel-build-arg=--distdir=" + distdir])
                        work = calls[-1][calls[-1].index("--work-dir") + 1]
                        self.assertNotEqual(Path(distdir), Path(work))
                        self.assertNotIn(Path(work), Path(distdir).parents)


if __name__ == "__main__":
    unittest.main()
