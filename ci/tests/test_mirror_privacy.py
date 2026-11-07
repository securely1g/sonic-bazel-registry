"""Private mirror locations must not survive in published CI evidence."""
from __future__ import annotations

import base64
import bz2
import contextlib
import gzip
import hashlib
import importlib.util
import io
import json
import lzma
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tarfile
import tempfile
import unittest
from unittest import mock
from urllib.parse import quote
import zipfile


SPEC = importlib.util.spec_from_file_location(
    "mirror_privacy", Path(__file__).resolve().parents[1] / "mirror_privacy.py")
assert SPEC and SPEC.loader
privacy = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(privacy)
URL = "https://private-mirror.example.invalid/archive/debian/20260727T143429Z/"
HOST = "private-mirror.example.invalid"


def tar_bytes(name, payload):
    result = io.BytesIO()
    with tarfile.open(fileobj=result, mode="w") as archive:
        member = tarfile.TarInfo(name)
        member.size = len(payload)
        archive.addfile(member, io.BytesIO(payload))
    return result.getvalue()


def ar_bytes(name, payload):
    header = (f"{name + '/':<16}{0:<12}{0:<6}{0:<6}{'100644':<8}{len(payload):<10}`\n").encode()
    assert len(header) == 60
    return b"!<arch>\n" + header + payload + (b"\n" if len(payload) % 2 else b"")


class PrivacyTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.artifacts = self.root / "artifacts"
        self.artifacts.mkdir()
        self.redactor = privacy.Redactor([URL])

    def assert_rejected_without_disclosure(self):
        with self.assertRaises(privacy.PrivacyError) as error:
            self.redactor.scrub_and_scan(self.artifacts)
        self.assertNotIn(HOST, str(error.exception))
        self.assertNotIn(URL, str(error.exception))

    def test_console_redacts_url_host_encoded_and_escaped_forms(self):
        values = [URL, HOST, HOST.upper(), quote(URL, safe=""),
                  URL.replace("/", r"\/"), re.escape(URL), json.dumps(re.escape(URL))[1:-1]]
        for value in values:
            with self.subTest(form=value):
                self.assertEqual(self.redactor.redact("before " + value + " after"),
                                 "before [private-mirror] after")
        self.assertEqual(self.redactor.redact("https://snapshot.debian.org/archive/debian/"),
                         "https://snapshot.debian.org/archive/debian/")

    def test_diagnostic_files_are_scrubbed_and_have_digest_receipts(self):
        raw = ("failure " + URL + "pool/foo.deb\nlookup " + HOST + "\n").encode()
        originals = {name: raw for name in ("build.log", "test.log", "test.xml", "MODULE.bazel.lock")}
        originals["build-events.jsonl"] = (json.dumps({"aborted": {"description": raw.decode()}}) + "\n").encode()
        for name, data in originals.items():
            (self.artifacts / name).write_bytes(data)
        self.redactor.scrub_and_scan(self.artifacts)
        receipt = json.loads((self.artifacts / "mirror-redaction.json").read_text())
        self.assertFalse(receipt["payloads_modified"])
        self.assertEqual(len(receipt["files"]), 5)
        for record in receipt["files"]:
            payload = (self.artifacts / record["path"]).read_bytes()
            self.assertNotIn(HOST.encode(), payload)
            self.assertEqual(record["original_sha256"], hashlib.sha256(originals[record["path"]]).hexdigest())
            self.assertEqual(record["sanitized_sha256"], hashlib.sha256(payload).hexdigest())
        # A second scan does not erase the first scan's redaction provenance.
        self.redactor.scrub_and_scan(self.artifacts)
        self.assertEqual(json.loads((self.artifacts / "mirror-redaction.json").read_text()), receipt)

    def test_cross_command_stdio_are_scrubbed_with_digest_receipts(self):
        spec = importlib.util.spec_from_file_location(
            "cross_toolchain", Path(__file__).resolve().parents[1] / "cross_toolchain.py")
        cross = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cross)
        warning = ("WARNING: Download from " + URL + "pool/main/example.deb failed: "
                   "class java.io.FileNotFoundException GET returned 404 Not Found\n")

        def emit_graph(command, **kwargs):
            kwargs["stdout"].write('{"name":"example","version":"1"}\n')
            kwargs["stderr"].write(warning)
            return subprocess.CompletedProcess(command, 0)

        # Exercise the real module-graph diagnostic writer with controlled
        # subprocess output; this does not identify a particular failed CI file.
        with mock.patch.object(cross.subprocess, "run", side_effect=emit_graph):
            cross.module_graph(["bazel"], [], self.root, self.artifacts, "cross-native-graph")
        stdout = self.artifacts / "runtime-probe.stdout"
        stdout.write_text("download " + quote(URL, safe="") + "\n")
        originals = {name: (self.artifacts / name).read_bytes()
                     for name in ("cross-native-graph.stderr", "runtime-probe.stdout")}
        payloads = {"library.so": b"\x7fELF\x00ordinary library",
                    "runtime.tar.gz": gzip.compress(tar_bytes("usr/share/example", b"ordinary payload"))}
        for name, content in payloads.items():
            (self.artifacts / name).write_bytes(content)

        self.redactor.scrub_and_scan(self.artifacts)

        self.assertEqual((self.artifacts / "cross-native-graph.stderr").read_text(),
                         warning.replace(URL, privacy.MARKER))
        self.assertEqual(stdout.read_text(), "download [private-mirror]\n")
        receipt = json.loads((self.artifacts / "mirror-redaction.json").read_text())
        self.assertFalse(receipt["payloads_modified"])
        self.assertEqual({record["path"] for record in receipt["files"]}, set(originals))
        for record in receipt["files"]:
            self.assertEqual(record["original_sha256"], hashlib.sha256(originals[record["path"]]).hexdigest())
            self.assertEqual(record["sanitized_sha256"],
                             hashlib.sha256((self.artifacts / record["path"]).read_bytes()).hexdigest())
        for name, content in payloads.items():
            self.assertEqual((self.artifacts / name).read_bytes(), content)

    def test_compressed_stdio_diagnostic_leaks_are_rejected_without_rewrite(self):
        warning = ("failed " + URL + "pool/main/example.deb\n").encode()
        for name, content in (
                ("cross-native-graph.stderr.gz", gzip.compress(warning)),
                ("runtime.tar.gz", gzip.compress(tar_bytes("diagnostics/probe.stdout", warning)))):
            with self.subTest(archive=name):
                path = self.artifacts / name
                path.write_bytes(content)
                self.assert_rejected_without_disclosure()
                self.assertEqual(path.read_bytes(), content)
                path.unlink()

    def test_bep_split_progress_is_removed_without_changing_event_graph(self):
        safe_contents = base64.b64encode(b"ordinary inline file").decode()
        records = [
            {"id": {"progress": {"opaqueCount": 1}}, "children": [{"progress": {"opaqueCount": 2}}],
             "progress": {"stdout": "download https://" + HOST[:14], "stderr": "public status"}},
            {"id": {"progress": {"opaqueCount": 2}}, "progress": {"stdout": HOST[14:] + "/archive/"}},
            {"id": {"namedSet": {"id": "outputs"}}, "namedSetOfFiles": {"files": [
                {"name": "result.txt", "pathPrefix": ["bazel-out"], "contents": safe_contents}]}},
            {"id": {"testResult": {"label": "//:consumer"}}, "testResult": {"status": "PASSED"}},
            {"aborted": {"description": "separate complete address " + URL}},
        ]
        expected = json.loads(json.dumps(records))
        for record in expected[:2]:
            record["progress"] = {}
        expected[-1]["aborted"]["description"] = "separate complete address [private-mirror]"
        original = ("\n".join(json.dumps(record) for record in records) + "\n").encode()
        path = self.artifacts / "build-events.jsonl"
        path.write_bytes(original)
        (self.artifacts / "build.log").write_text("download " + URL + "\n")
        self.redactor.scrub_and_scan(self.artifacts)
        self.assertEqual([json.loads(line) for line in path.read_text().splitlines()], expected)
        self.assertEqual((self.artifacts / "build.log").read_text(), "download [private-mirror]\n")
        changes = json.loads((self.artifacts / "mirror-redaction.json").read_text())["files"]
        record = next(item for item in changes if item["path"] == path.name)
        self.assertEqual(record["original_sha256"], hashlib.sha256(original).hexdigest())
        self.assertEqual(record["sanitized_sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertEqual(record["bep_progress_fields_removed"], 3)

    def test_bep_inline_base64_file_leak_is_rejected_without_rewriting_payload(self):
        path = self.artifacts / "test-events.jsonl"
        payload = b"\x7fELF" + HOST.encode() + b"\x00"
        for extra in ({"name": "library.so", "pathPrefix": ["bazel-out"]}, {}):
            with self.subTest(file_metadata=extra):
                record = {"id": {"testResult": {"label": "//:consumer"}},
                          "testResult": {"testActionOutput": [
                              {**extra, "contents": base64.b64encode(payload).decode()}]}}
                raw = (json.dumps(record) + "\n").encode()
                path.write_bytes(raw)
                self.assert_rejected_without_disclosure()
                self.assertEqual(path.read_bytes(), raw)

    def test_malformed_bep_cannot_bypass_inline_file_inspection(self):
        (self.artifacts / "test-events.jsonl").write_text('{"progress":')
        self.assert_rejected_without_disclosure()

    def test_scrubbing_handles_secret_across_chunk_boundaries(self):
        path = self.artifacts / "build.log"
        raw = b"A" * 511 + URL.encode() + b"Z" * 700
        path.write_bytes(raw)
        with mock.patch.object(privacy, "CHUNK_SIZE", 64):
            self.redactor.scrub_and_scan(self.artifacts)
        self.assertEqual(path.read_bytes(), b"A" * 511 + b"[private-mirror]" + b"Z" * 700)

    def test_hardlinked_source_log_is_preserved_and_index_tracks_sanitized_copy(self):
        source = self.root / "source.log"
        source.write_text("failed " + URL)
        target = self.artifacts / "test.log"
        os.link(source, target)
        original = source.read_bytes()
        (self.artifacts / "test-results.json").write_text(json.dumps([{
            "label": "//:consumer_test", "files": [{"path": "test.log",
                "sha256": hashlib.sha256(original).hexdigest(), "size": len(original)}]}]))
        self.redactor.scrub_and_scan(self.artifacts)
        self.assertEqual(source.read_bytes(), original)
        self.assertNotEqual(source.stat().st_ino, target.stat().st_ino)
        record = json.loads((self.artifacts / "test-results.json").read_text())[0]["files"][0]
        self.assertEqual(record["sha256"], hashlib.sha256(target.read_bytes()).hexdigest())
        self.assertEqual(record["size"], target.stat().st_size)

    def test_receipt_replacement_does_not_follow_an_existing_symlink(self):
        binary = self.artifacts / "library.so"
        binary.write_bytes(b"\x7fELF unchanged runtime")
        (self.artifacts / "mirror-redaction.json").symlink_to("library.so")
        (self.artifacts / "build.log").write_text(URL)
        self.redactor.scrub_and_scan(self.artifacts)
        self.assertEqual(binary.read_bytes(), b"\x7fELF unchanged runtime")
        self.assertFalse((self.artifacts / "mirror-redaction.json").is_symlink())

    def test_binary_leak_across_scan_boundary_is_rejected_not_changed(self):
        path = self.artifacts / "library.so"
        payload = b"\x7fELF" + b"A" * 507 + HOST.encode() + b"\x00"
        path.write_bytes(payload)
        with mock.patch.object(privacy, "CHUNK_SIZE", 64):
            self.assert_rejected_without_disclosure()
        self.assertEqual(path.read_bytes(), payload)

    def test_raw_scan_finds_all_encoded_forms_across_chunks(self):
        redactor = privacy.Redactor([URL, "https://mïrror.example.invalid/a path/"])
        path = self.artifacts / "payload.bin"
        with mock.patch.object(privacy, "CHUNK_SIZE", 7):
            for pattern in redactor.patterns:
                with self.subTest(pattern=pattern):
                    payload = b"\xff" * 511 + pattern.encode().swapcase() + b"\x00"
                    path.write_bytes(payload)
                    with self.assertRaises(privacy.PrivacyError):
                        redactor.scrub_and_scan(self.artifacts)
                    self.assertEqual(path.read_bytes(), payload)

            safe = b"\xff" * 511 + b"PRIVATE-MIRRORxEXAMPLExINVALID\x00"
            path.write_bytes(safe)
            redactor.scrub_and_scan(self.artifacts)
            self.assertEqual(path.read_bytes(), safe)

    def test_payload_errors_identify_only_the_validated_outer_artifact(self):
        (self.artifacts / "outputs").mkdir()
        for name, payload in (
                ("library.so", b"\x7fELF\x00" + HOST.encode()),
                ("runtime.tar.gz", gzip.compress(tar_bytes(HOST + "/untrusted-inner-name", b"payload")))):
            with self.subTest(artifact=name):
                path = self.artifacts / "outputs" / name
                path.write_bytes(payload)
                with self.assertRaises(privacy.PrivacyError) as error:
                    self.redactor.scrub_and_scan(self.artifacts)
                message = str(error.exception)
                self.assertIn(f'artifact "outputs/{name}"', message)
                self.assertNotIn(HOST, message)
                self.assertNotIn("untrusted-inner-name", message)
                self.assertNotIn(str(self.artifacts), message)
                self.assertEqual(path.read_bytes(), payload)
                path.unlink()

    def test_secret_bearing_filenames_are_not_added_to_errors(self):
        for name in (HOST + ".so", quote(URL, safe="") + ".so"):
            with self.subTest(filename=name):
                path = self.artifacts / name
                path.write_bytes(b"ordinary payload")
                with self.assertRaises(privacy.PrivacyError) as error:
                    self.redactor.scrub_and_scan(self.artifacts)
                self.assertEqual(str(error.exception),
                                 "Private mirror location remains in validation evidence")
                path.unlink()

    def test_raw_scanner_errors_remain_generic(self):
        (self.artifacts / "library.so").write_bytes(b"\x7fELF ordinary payload")
        with mock.patch.object(self.redactor, "_scan_stream", side_effect=OSError("could not open " + URL)):
            with self.assertRaises(privacy.PrivacyError) as error:
                self.redactor.scrub_and_scan(self.artifacts)
        self.assertEqual(str(error.exception), "Could not inspect private-mirror validation evidence")

    def test_unmodified_payload_and_clean_log_preserve_bytes_modes_and_mtime(self):
        values = {"library.so": b"\x7fELF unchanged runtime", "build.log": b"public failure\n",
                  "runtime.tar.gz": gzip.compress(tar_bytes("usr/lib/libexample.so", b"ELF"))}
        for name, payload in values.items():
            path = self.artifacts / name
            path.write_bytes(payload)
            path.chmod(0o640)
            os.utime(path, ns=(123456789, 123456789))
        self.redactor.scrub_and_scan(self.artifacts)
        for name, payload in values.items():
            path = self.artifacts / name
            self.assertEqual(path.read_bytes(), payload)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o640)
            self.assertEqual(path.stat().st_mtime_ns, 123456789)
        self.assertFalse((self.artifacts / "mirror-redaction.json").exists())

    def test_nested_compressed_archive_leaks_are_rejected(self):
        for compressor, suffix in ((gzip.compress, "gz"), (bz2.compress, "bz2"), (lzma.compress, "xz")):
            with self.subTest(compression=suffix):
                inner = compressor(tar_bytes("test.log", ("download failed " + URL).encode()))
                outer = self.artifacts / "outputs.zip"
                with zipfile.ZipFile(outer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                    archive.writestr("nested.tar." + suffix, inner)
                original = outer.read_bytes()
                self.assert_rejected_without_disclosure()
                self.assertEqual(outer.read_bytes(), original)
                outer.unlink()

    def test_debian_ar_package_compressed_payload_is_scanned(self):
        payload = lzma.compress(tar_bytes("usr/share/example/config", HOST.encode()))
        package = ar_bytes("data.tar.xz", payload)
        path = self.artifacts / "runtime.deb"
        path.write_bytes(package)
        self.assert_rejected_without_disclosure()
        self.assertEqual(path.read_bytes(), package)

    def test_private_filename_and_archive_member_names_are_rejected(self):
        path = self.artifacts / (HOST + ".log")
        path.write_text("no private data in contents")
        self.assert_rejected_without_disclosure()
        path.unlink()
        (self.artifacts / "runtime.tar").write_bytes(tar_bytes(HOST + "/file", b"safe"))
        self.assert_rejected_without_disclosure()

    def test_symlink_escape_is_rejected_without_reading_target(self):
        outside = self.root / "private-target"
        outside.write_text(URL)
        (self.artifacts / "target").symlink_to(outside)
        self.assert_rejected_without_disclosure()
        self.assertEqual(outside.read_text(), URL)

    def test_internal_symlink_uses_the_checked_target(self):
        (self.artifacts / "build.log").write_text(HOST)
        (self.artifacts / "linked.log").symlink_to("build.log")
        self.redactor.scrub_and_scan(self.artifacts)
        self.assertEqual((self.artifacts / "linked.log").read_text(), privacy.MARKER)

    def test_secret_config_accidentally_copied_to_evidence_is_rejected(self):
        (self.artifacts / "downloader.cfg").write_text("rewrite example.invalid " + URL)
        self.assert_rejected_without_disclosure()

    def test_unsupported_and_corrupt_archives_fail_closed(self):
        for name, payload in (("archive.7z", b"7z\xbc\xaf\x27\x1c"),
                              ("archive.zip", b"broken zip bytes"),
                              ("archive.gz", b"\x1f\x8bcorrupt")):
            with self.subTest(archive=name):
                path = self.artifacts / name
                path.write_bytes(payload)
                self.assert_rejected_without_disclosure()
                path.unlink()

    def test_missing_zstd_scanner_fails_closed(self):
        (self.artifacts / "archive.zst").write_bytes(b"\x28\xb5\x2f\xfd")
        with mock.patch.object(privacy.shutil, "which", return_value=None):
            self.assert_rejected_without_disclosure()

    @unittest.skipUnless(shutil.which("zstd"), "zstd is not installed")
    def test_zstd_tar_member_leak_is_rejected(self):
        payload = tar_bytes("usr/share/example/config", HOST.encode())
        result = subprocess.run([shutil.which("zstd"), "-q", "-c"], input=payload,
                                capture_output=True, check=True)
        (self.artifacts / "archive.tar.zst").write_bytes(result.stdout)
        self.assert_rejected_without_disclosure()

    def test_no_secrets_preserves_existing_artifact_handling(self):
        path = self.artifacts / "build.log"
        path.write_text(URL)
        (self.artifacts / "old.zip").write_bytes(b"fixture bytes, not an archive")
        privacy.Redactor([]).scrub_and_scan(self.artifacts)
        self.assertEqual(path.read_text(), URL)

    def budgeted(self, blocks):
        block = os.statvfs(self.artifacts).f_frsize
        budget = privacy.TemporaryBudget(self.root, maximum_bytes=blocks * block,
                                         minimum_free_bytes=block)
        return privacy.Redactor([URL], temporary_budget=budget), budget, block

    def test_budget_releases_sequential_archives_without_counting_plain_elf(self):
        redactor, budget, block = self.budgeted(3)
        payload = tar_bytes("file", b"safe")
        self.assertLessEqual(len(payload), budget.maximum_bytes)
        for name in ("first.tar", "second.tar"):
            (self.artifacts / name).write_bytes(payload)
        (self.artifacts / "plain.so").write_bytes(b"\x7fELF" + b"x" * (10 * block))
        redactor.scrub_and_scan(self.artifacts)
        self.assertEqual(budget.usage(), {"maximum_bytes": 3 * block,
            "minimum_free_bytes": block, "live_bytes": 0, "peak_bytes": 3 * block,
            "open_files": 0, "peak_open_files": 1})
        self.assertEqual((self.artifacts / "first.tar").read_bytes(), payload)

    def test_budget_counts_nested_parent_spools_and_fails_closed(self):
        redactor, budget, block = self.budgeted(3)
        payload = gzip.compress(tar_bytes("file", b"safe"))
        path = self.artifacts / "nested.tar.gz"
        path.write_bytes(payload)
        with self.assertRaisesRegex(privacy.PrivacyError, "temporary-space budget exceeded"):
            redactor.scrub_and_scan(self.artifacts)
        self.assertEqual(path.read_bytes(), payload)
        self.assertEqual(budget.live_bytes, 0)
        self.assertEqual(budget.open_files, 0)
        self.assertEqual(budget.peak_open_files, 2)
        self.assertLessEqual(budget.peak_bytes, 3 * block)
        redactor, budget, block = self.budgeted(4)
        redactor.scrub_and_scan(self.artifacts)
        self.assertEqual(budget.peak_bytes, 4 * block)
        self.assertEqual(budget.live_bytes, 0)
        self.assertEqual(budget.open_files, 0)
        self.assertEqual(path.read_bytes(), payload)

    def test_budget_includes_bep_replacement_while_inline_archive_is_scanned(self):
        redactor, budget, block = self.budgeted(4)
        payload = gzip.compress(tar_bytes("file", b"safe"))
        records = [{"id": {"progress": {"opaqueCount": 1}}, "progress": {"stdout": "safe"}},
                   {"testResult": {"files": [{"name": "inline.tar.gz",
                       "contents": base64.b64encode(payload).decode()}]}}]
        original = ("\n".join(json.dumps(item) for item in records) + "\n").encode()
        path = self.artifacts / "test-events.jsonl"
        path.write_bytes(original)
        with self.assertRaisesRegex(privacy.PrivacyError, "temporary-space budget exceeded"):
            redactor.scrub_and_scan(self.artifacts)
        self.assertEqual(budget.peak_open_files, 3)
        self.assertEqual(budget.live_bytes, 0)
        self.assertEqual(budget.open_files, 0)
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(list(self.artifacts.glob(".mirror-redaction-*")), [])

    def test_budget_success_preserves_scrubbing_and_index_linkage(self):
        redactor, budget, _ = self.budgeted(64)
        path = self.artifacts / "test.log"
        original = (URL + "\n").encode()
        path.write_bytes(original)
        (self.artifacts / "test-results.json").write_text(json.dumps([{
            "files": [{"path": "test.log", "sha256": hashlib.sha256(original).hexdigest(),
                       "size": len(original)}]}]))
        redactor.scrub_and_scan(self.artifacts)
        self.assertEqual(path.read_bytes(), (privacy.MARKER + "\n").encode())
        index = json.loads((self.artifacts / "test-results.json").read_text())
        self.assertEqual(index[0]["files"][0]["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertEqual(budget.live_bytes, 0)
        self.assertEqual(budget.open_files, 0)
        self.assertGreater(budget.peak_bytes, 0)
        self.assertEqual(list(self.artifacts.glob(".mirror-redaction-*")), [])

    def test_budget_preserves_nested_privacy_rejection_and_closes_spools(self):
        redactor, budget, _ = self.budgeted(64)
        payload = gzip.compress(tar_bytes("file", HOST.encode()))
        path = self.artifacts / "nested.tar.gz"
        path.write_bytes(payload)
        with self.assertRaises(privacy.PrivacyError) as error:
            redactor.scrub_and_scan(self.artifacts)
        self.assertNotIn(HOST, str(error.exception))
        self.assertEqual(path.read_bytes(), payload)
        self.assertEqual(budget.live_bytes, 0)
        self.assertEqual(budget.open_files, 0)

    def test_budget_checks_actual_growth_below_maximum_headroom(self):
        # A small spool may fit while the configured maximum would not.
        # Each actual write still preserves the separate filesystem floor.
        for free_blocks, succeeds in ((4, True), (3, False)):
            with self.subTest(free_blocks=free_blocks):
                redactor, budget, block = self.budgeted(16)
                path = self.artifacts / "runtime.tar"
                original = tar_bytes("file", b"safe")
                path.write_bytes(original)
                self.assertEqual(len(original), 10240)
                self.assertEqual(budget.maximum_bytes, 16 * block)
                self.assertEqual(budget.minimum_free_bytes, block)
                def available(_):
                    return mock.Mock(f_bavail=free_blocks - budget.live_bytes // block,
                                     f_frsize=block)
                with mock.patch.object(privacy.os, "statvfs", side_effect=available):
                    if succeeds:
                        redactor.scrub_and_scan(self.artifacts)
                        self.assertEqual(budget.peak_bytes, 3 * block)
                    else:
                        with self.assertRaisesRegex(privacy.PrivacyError, "headroom is insufficient"):
                            redactor.scrub_and_scan(self.artifacts)
                        self.assertLess(budget.peak_bytes, budget.maximum_bytes)
                self.assertEqual(path.read_bytes(), original)
                self.assertEqual(budget.live_bytes, 0)
                self.assertEqual(budget.open_files, 0)

    def test_budget_checks_fresh_headroom_before_scan_and_each_write(self):
        redactor, budget, block = self.budgeted(16)
        path = self.artifacts / "runtime.tar"
        original = tar_bytes("file", b"safe")
        path.write_bytes(original)
        low = mock.Mock(f_bavail=0, f_frsize=block)
        high = mock.Mock(f_bavail=1000, f_frsize=block)
        for readings in ([low], [high, high, low]):
            with self.subTest(readings=len(readings)), mock.patch.object(
                    privacy.os, "statvfs", side_effect=readings):
                with self.assertRaisesRegex(privacy.PrivacyError, "headroom is insufficient"):
                    redactor.scrub_and_scan(self.artifacts)
            self.assertEqual(budget.live_bytes, 0)
            self.assertEqual(budget.open_files, 0)
            self.assertEqual(path.read_bytes(), original)

    def test_budget_releases_reserved_bytes_after_write_error(self):
        redactor, budget, _ = self.budgeted(16)
        (self.artifacts / "runtime.tar").write_bytes(tar_bytes("file", b"safe"))
        original_factory = tempfile.TemporaryFile

        class FailedWrite:
            def __init__(self, **options):
                self.raw = original_factory(**options)

            def write(self, value):
                raise OSError("private transport " + URL)

            def __getattr__(self, name):
                return getattr(self.raw, name)

        with mock.patch.object(privacy.tempfile, "TemporaryFile", side_effect=FailedWrite):
            with self.assertRaises(privacy.PrivacyError) as error:
                redactor.scrub_and_scan(self.artifacts)
        self.assertNotIn(HOST, str(error.exception))
        self.assertGreater(budget.peak_bytes, 0)
        self.assertEqual(budget.live_bytes, 0)
        self.assertEqual(budget.open_files, 0)

    def test_budget_partial_write_and_closed_file_error_release_accounting(self):
        original_factory = tempfile.TemporaryFile
        path = self.artifacts / "runtime.tar"
        original = tar_bytes("file", b"safe")
        path.write_bytes(original)

        class FailedFile:
            def __init__(self, failure, **options):
                self.raw, self.failure = original_factory(**options), failure

            def write(self, value):
                return self.raw.write(value[:-1] if self.failure == "partial" else value)

            def close(self):
                self.raw.close()
                if self.failure == "close":
                    raise OSError("private transport " + URL)

            def __getattr__(self, name):
                return getattr(self.raw, name)

        for failure in ("partial", "close"):
            redactor, budget, _ = self.budgeted(16)
            with self.subTest(failure=failure), mock.patch.object(
                    privacy.tempfile, "TemporaryFile",
                    side_effect=lambda **options: FailedFile(failure, **options)):
                with self.assertRaises(privacy.PrivacyError) as error:
                    redactor.scrub_and_scan(self.artifacts)
            self.assertNotIn(HOST, str(error.exception))
            self.assertGreater(budget.peak_bytes, 0)
            self.assertEqual(budget.live_bytes, 0)
            self.assertEqual(budget.open_files, 0)
            self.assertEqual(path.read_bytes(), original)

    def test_budget_rejects_invalid_limits_and_temporary_filesystems(self):
        for maximum, minimum in ((True, 0), (0, 0), (-1, 0), (4096, -1), (4096, False)):
            with self.subTest(maximum=maximum, minimum=minimum):
                with self.assertRaises(privacy.PrivacyError):
                    privacy.TemporaryBudget(self.root, maximum_bytes=maximum, minimum_free_bytes=minimum)
        link = self.root / "linked"
        link.symlink_to(self.artifacts, target_is_directory=True)
        with self.assertRaises(privacy.PrivacyError):
            privacy.TemporaryBudget(link, maximum_bytes=4096, minimum_free_bytes=0)
        redactor, budget, _ = self.budgeted(16)
        budget.device += 1
        with self.assertRaisesRegex(privacy.PrivacyError, "different filesystems"):
            redactor.scrub_and_scan(self.artifacts)
        self.assertEqual(budget.open_files, 0)

    def test_mask_commands_are_only_emitted_inside_github_actions(self):
        output = io.StringIO()
        with mock.patch.dict(os.environ, {"GITHUB_ACTIONS": "false"}), contextlib.redirect_stdout(output):
            self.redactor.mask_github()
        self.assertEqual(output.getvalue(), "")
        with mock.patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}), contextlib.redirect_stdout(output):
            self.redactor.mask_github()
        lines = output.getvalue().splitlines()
        self.assertTrue(all(line.startswith("::add-mask::") for line in lines))
        self.assertIn("::add-mask::" + HOST, lines)
        self.assertIn("::add-mask::" + URL, lines)


if __name__ == "__main__":
    unittest.main()
