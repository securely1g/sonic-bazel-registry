"""Exercise GitHub transport policy and verified distdir publication offline."""

from __future__ import annotations

import copy
import hashlib
from http.client import IncompleteRead
import importlib.util
import io
import json
from pathlib import Path
import stat
import struct
import tempfile
import unittest
from unittest import mock
from urllib.error import HTTPError, URLError
from urllib.request import Request
import warnings
import zipfile


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("github_sources", ROOT / "ci/github_sources.py")
GITHUB = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GITHUB)
URL = "https://github.com/example/tools/releases/download/v1.2/tools.zip"
PROVENANCE = "https://raw.githubusercontent.com/example/tools/" + "a" * 40 + "/lock.json"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def entry(name, data, path=None):
    result = {"name": name, "size": len(data), "sha256": sha(data), "provenance": PROVENANCE}
    if path is not None:
        result["path"] = path
    return result


def direct(name="tool.bin", data=b"locked tool bytes"):
    return {"url": URL.removesuffix(".zip") + ".bin", "size": len(data), "sha256": sha(data),
            "format": "file", "files": [entry(name, data)]}


def zipped(members=None, compression=zipfile.ZIP_DEFLATED):
    members = members or [("bin/tool", b"tool bytes"), ("bin/helper", b"helper bytes")]
    output = io.BytesIO()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with zipfile.ZipFile(output, "w", compression=compression) as archive:
            for name, data in members:
                archive.writestr(name, data)
    data = output.getvalue()
    files = [entry(name.rsplit("/", 1)[-1], payload, name) for name, payload in members]
    return {"url": URL, "size": len(data), "format": "zip", "files": files}, data


class Fixture(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.manifest = self.root / "inputs.json"
        self.distdir = self.root / "distdir"
        self.cache = self.root / "cache"
        self.receipt = self.root / "receipt.json"

    def write_manifest(self, *sources):
        self.manifest.write_text(json.dumps({"schema_version": 1, "sources": list(sources)}))
        return self.manifest

    def prepare(self, repository_cache=None):
        return GITHUB.prepare(self.manifest, self.distdir, self.cache, self.receipt, repository_cache)

    @staticmethod
    def supply(data):
        return lambda _source, destination: destination.write_bytes(data)


class ManifestTest(Fixture):
    def test_direct_and_member_pins_validate(self):
        archive, _ = zipped()
        self.write_manifest(direct(), archive)
        parsed, digest = GITHUB.load_manifest(self.manifest)
        self.assertEqual(parsed["sources"][1], archive)
        self.assertEqual(digest, sha(self.manifest.read_bytes()))

    def test_duplicate_json_keys_are_rejected(self):
        self.manifest.write_text('{"schema_version":1,"schema_version":1,"sources":[]}')
        with self.assertRaisesRegex(GITHUB.SourceError, "duplicate JSON key"):
            GITHUB.load_manifest(self.manifest)

    def test_unknown_schema_and_fields_are_rejected(self):
        original = {"schema_version": 1, "sources": [direct()]}
        changed = []
        for value in (2, True, 1.0):
            changed.append({**original, "schema_version": value})
        changed.append({**original, "fallback_url": "https://another.example/tool"})
        for container in ("source", "file"):
            value = copy.deepcopy(original)
            obj = value["sources"][0]
            if container == "file":
                obj = obj["files"][0]
            obj["fallback"] = "another.example"
            changed.append(value)
        for value in changed:
            with self.subTest(value=value):
                self.manifest.write_text(json.dumps(value))
                with self.assertRaises(GITHUB.SourceError):
                    GITHUB.load_manifest(self.manifest)

    def test_invalid_size_digest_and_provenance_are_rejected(self):
        cases = [("size", x) for x in (0, -1, True, 1.5, GITHUB.MAX_ASSET_BYTES + 1)]
        cases += [("sha256", x) for x in ("F" * 64, "a" * 63, None)]
        cases += [("provenance", x) for x in ("https://user:pass@example.test/lock", "http://example.test/lock",
                                              PROVENANCE + "?private=example", None, {})]
        for field, value in cases:
            with self.subTest(field=field, value=value):
                source = direct()
                source["files"][0][field] = value
                self.write_manifest(source)
                with self.assertRaises(GITHUB.SourceError):
                    GITHUB.load_manifest(self.manifest)

    def test_direct_asset_must_pin_the_same_whole_file(self):
        for field, value in (("sha256", "a" * 64), ("size", 18)):
            source = direct()
            source[field] = value
            self.write_manifest(source)
            with self.assertRaisesRegex(GITHUB.SourceError, "must agree"):
                GITHUB.load_manifest(self.manifest)
        source = direct()
        source.pop("sha256")
        self.write_manifest(source)
        with self.assertRaisesRegex(GITHUB.SourceError, "whole-file SHA256"):
            GITHUB.load_manifest(self.manifest)

    def test_unsafe_or_duplicate_output_names_are_rejected(self):
        for name in ("../tool", "/tool", "dir/tool", "..", "tool\\name", "tool\x00", ""):
            with self.subTest(name=name):
                self.write_manifest(direct(name=name))
                with self.assertRaisesRegex(GITHUB.SourceError, "basenames"):
                    GITHUB.load_manifest(self.manifest)
        self.write_manifest(direct(), direct())
        with self.assertRaisesRegex(GITHUB.SourceError, "basenames"):
            GITHUB.load_manifest(self.manifest)

    def test_zip_paths_must_be_exact_safe_unique_members(self):
        for path in ("../tool", "/tool", "bin/../tool", "bin//tool", "bin/./tool", "bin\\tool", "C:/tool"):
            source, _ = zipped()
            source["files"][0]["path"] = path
            self.write_manifest(source)
            with self.subTest(path=path), self.assertRaisesRegex(GITHUB.SourceError, "ZIP member path"):
                GITHUB.load_manifest(self.manifest)
        source, _ = zipped()
        source["files"][1]["path"] = source["files"][0]["path"]
        self.write_manifest(source)
        with self.assertRaisesRegex(GITHUB.SourceError, "selected more than once"):
            GITHUB.load_manifest(self.manifest)

    def test_manifest_size_is_bounded(self):
        self.manifest.write_bytes(b" " * (GITHUB.MAX_MANIFEST_BYTES + 1))
        with self.assertRaisesRegex(GITHUB.SourceError, "exceeds 1 MiB"):
            GITHUB.load_manifest(self.manifest)


class URLPolicyTest(unittest.TestCase):
    def test_canonical_release_and_commit_urls_are_accepted(self):
        for url in (URL, PROVENANCE,
                    "https://codeload.github.com/example/tools/zip/" + "a" * 40,
                    "https://codeload.github.com/example/tools/tar.gz/" + "b" * 40):
            GITHUB.validate_url(url)

    def test_other_hosts_floating_refs_and_credential_urls_are_rejected(self):
        for url in (URL.replace("github.com", "github.com.example.test"),
                    URL.replace("github.com", "other.example"), URL.replace("https:", "http:"),
                    URL.replace("github.com", "user:pass@github.com"),
                    URL.replace("github.com", "github.com:443"),
                    URL.replace("github.com", "github.com:"),
                    URL + "?token=example", URL + "#fragment", " " + URL,
                    URL.replace("v1.2", "latest"), URL.replace("tools.zip", "%2e%2e"),
                    PROVENANCE.replace("a" * 40, "main"),
                    "https://codeload.github.com/example/tools/zip/v1.2",
                    "https://release-assets.githubusercontent.com/asset"):
            with self.subTest(url=url), self.assertRaises(GITHUB.SourceError):
                GITHUB.validate_url(url)

    def test_redirect_handler_rejects_external_host_before_request_creation(self):
        request = Request(URL)
        handler = GITHUB.GitHubRedirectHandler()
        for destination in ("https://external.example/input", "http://github.com/input",
                            "https://release-assets.githubusercontent.com.evil.test/input",
                            "https://user:pass@objects.githubusercontent.com/input",
                            "https://github.com/login?token=example"):
            with self.subTest(destination=destination), self.assertRaises(GITHUB.SourceError):
                handler.redirect_request(request, None, 302, "Found", {}, destination)
        signed = "https://release-assets.githubusercontent.com/asset?signature=test-only"
        redirected = handler.redirect_request(request, None, 302, "Found", {}, signed)
        self.assertEqual(redirected.full_url, signed)
        self.assertIsNone(redirected.get_header("Authorization"))


class FakeResponse(io.BytesIO):
    def __init__(self, data, *, status=200, length=None, url=URL):
        super().__init__(data)
        self.status = status
        self.headers = {} if length is None else {"Content-Length": length}
        self.url = url
        self.read_sizes = []

    def geturl(self):
        return self.url

    def read(self, size=-1):
        if size < 0:
            raise AssertionError("Download used an unbounded read")
        self.read_sizes.append(size)
        return super().read(size)


class DownloadTest(Fixture):
    def test_download_streams_only_github_without_authorization(self):
        data = b"locked tool bytes"
        response = FakeResponse(data, length=str(len(data)),
                                url="https://release-assets.githubusercontent.com/asset?signature=test-only")
        opener = mock.Mock()
        opener.open.return_value = response
        with mock.patch.object(GITHUB, "build_opener", return_value=opener):
            GITHUB.download(direct(), self.root / "asset")
        self.assertEqual((self.root / "asset").read_bytes(), data)
        request = opener.open.call_args.args[0]
        self.assertIsNone(request.get_header("Authorization"))
        self.assertEqual(opener.open.call_count, 1)
        self.assertTrue(all(n <= GITHUB.CHUNK_BYTES for n in response.read_sizes))

    def test_download_rejects_size_header_status_and_final_host_failures(self):
        responses = [FakeResponse(b"a" * 18), FakeResponse(b"a" * 16),
                     FakeResponse(b"a" * 17, length="18"), FakeResponse(b"a" * 17, length="bad"),
                     FakeResponse(b"a" * 17, status=206),
                     FakeResponse(b"a" * 17, url="https://external.example/asset")]
        for response in responses:
            opener = mock.Mock()
            opener.open.return_value = response
            with mock.patch.object(GITHUB, "build_opener", return_value=opener):
                with self.assertRaises(GITHUB.SourceError):
                    GITHUB.download(direct(), self.root / "asset")
            self.assertEqual(opener.open.call_count, 1)

    def test_transport_errors_do_not_expose_signed_urls_or_retry(self):
        marker = "signature=do-not-print-test-marker"
        errors = [URLError("https://release-assets.githubusercontent.com/asset?" + marker),
                  HTTPError(URL + "?" + marker, 503, marker, {}, None),
                  IncompleteRead(b"private-test-marker")]
        for error in errors:
            opener = mock.Mock()
            opener.open.side_effect = error
            with mock.patch.object(GITHUB, "build_opener", return_value=opener):
                with self.assertRaises(GITHUB.SourceError) as caught:
                    GITHUB.download(direct(), self.root / "asset")
            self.assertNotIn(marker, str(caught.exception))
            self.assertNotIn("private-test-marker", str(caught.exception))
            self.assertTrue(caught.exception.__suppress_context__)
            self.assertEqual(opener.open.call_count, 1)

    def test_transfer_deadline_stops_without_publishing(self):
        opener = mock.Mock()
        opener.open.return_value = FakeResponse(b"locked tool bytes")
        with mock.patch.object(GITHUB, "build_opener", return_value=opener), \
                mock.patch.object(GITHUB.time, "monotonic", side_effect=[0, 901]):
            with self.assertRaisesRegex(GITHUB.SourceError, "deadline"):
                GITHUB.download(direct(), self.root / "asset")


class PreparationTest(Fixture):
    def test_zip_download_publishes_only_selected_verified_members_and_receipt(self):
        source, data = zipped()
        self.write_manifest(source)
        with mock.patch.object(GITHUB, "download", side_effect=self.supply(data)) as download:
            result = self.prepare()
        self.assertEqual(download.call_count, 1)
        self.assertEqual((self.distdir / "tool").read_bytes(), b"tool bytes")
        self.assertEqual((self.distdir / "helper").read_bytes(), b"helper bytes")
        self.assertEqual(set(p.name for p in self.distdir.iterdir()), {"tool", "helper"})
        self.assertEqual((self.distdir / "tool").stat().st_mode & 0o777, 0o644)
        self.assertEqual(json.loads(self.receipt.read_text()), result)
        self.assertFalse(result["sources"][0]["whole_source_digest_declared"])
        self.assertEqual(result["manifest_sha256"], sha(self.manifest.read_bytes()))

    def test_distdir_and_repository_cache_reuse_are_reverified_without_network(self):
        source, _ = zipped()
        self.write_manifest(source)
        self.distdir.mkdir()
        (self.distdir / "tool").write_bytes(b"tool bytes")
        repository = self.root / "repository"
        entry = source["files"][1]
        candidate = repository / "content_addressable" / "sha256" / entry["sha256"] / "file"
        candidate.parent.mkdir(parents=True)
        candidate.write_bytes(b"helper bytes")
        with mock.patch.object(GITHUB, "download", side_effect=AssertionError("network")):
            result = self.prepare(repository)
        self.assertEqual([f["source"] for f in result["files"]], ["distdir", "repository-cache"])

    def test_verified_asset_cache_reuse_and_corrupt_cache_refetch(self):
        source, data = zipped()
        self.write_manifest(source)
        with mock.patch.object(GITHUB, "download", side_effect=self.supply(data)):
            self.prepare()
        for path in self.distdir.iterdir():
            path.unlink()
        with mock.patch.object(GITHUB, "download", side_effect=AssertionError("network")):
            result = self.prepare()
        self.assertEqual({f["source"] for f in result["files"]}, {"asset-cache"})
        for path in self.distdir.iterdir():
            path.unlink()
        next(self.cache.glob("*.asset")).write_bytes(b"corrupt")
        with mock.patch.object(GITHUB, "download", side_effect=self.supply(data)) as download:
            result = self.prepare()
        self.assertEqual(download.call_count, 1)
        self.assertEqual({f["source"] for f in result["files"]}, {"github"})

    def test_wrong_cached_bytes_and_symlinks_are_not_trusted(self):
        source = direct()
        self.write_manifest(source)
        self.distdir.mkdir()
        outside = self.root / "outside"
        outside.write_bytes(b"locked tool bytes")
        target = self.distdir / "tool.bin"
        target.symlink_to(outside)
        with mock.patch.object(GITHUB, "download", side_effect=self.supply(b"locked tool bytes")) as download:
            self.prepare()
        self.assertEqual(download.call_count, 1)
        self.assertFalse(target.is_symlink())
        self.assertEqual(outside.read_bytes(), b"locked tool bytes")
        target.write_bytes(b"wrong cached data")
        with mock.patch.object(GITHUB, "download", side_effect=AssertionError("network")):
            self.prepare()
        self.assertEqual(target.read_bytes(), b"locked tool bytes")
        target.write_bytes(b"wrong cached data")
        next(self.cache.glob("*.asset")).unlink()
        with mock.patch.object(GITHUB, "download", side_effect=GITHUB.SourceError("unavailable")):
            with self.assertRaisesRegex(GITHUB.SourceError, "unavailable"):
                self.prepare()
        self.assertEqual(target.read_bytes(), b"wrong cached data")

    def test_bad_last_member_changes_no_distdir_file_or_receipt(self):
        source, data = zipped()
        source["files"][-1]["sha256"] = "a" * 64
        self.write_manifest(source)
        self.distdir.mkdir()
        (self.distdir / "tool").write_bytes(b"old file preserved")
        (self.distdir / "unrelated").write_bytes(b"unrelated")
        with mock.patch.object(GITHUB, "download", side_effect=self.supply(data)):
            with self.assertRaisesRegex(GITHUB.SourceError, "SHA256"):
                self.prepare()
        self.assertEqual((self.distdir / "tool").read_bytes(), b"old file preserved")
        self.assertEqual((self.distdir / "unrelated").read_bytes(), b"unrelated")
        self.assertFalse((self.distdir / "helper").exists())
        self.assertFalse(self.receipt.exists())

    def test_later_source_failure_publishes_no_partial_set(self):
        self.write_manifest(direct("first"), direct("second", b"second input"))
        def supply(source, path):
            if source["files"][0]["name"] == "first":
                path.write_bytes(b"locked tool bytes")
            else:
                raise GITHUB.SourceError("GitHub unavailable")
        with mock.patch.object(GITHUB, "download", side_effect=supply):
            with self.assertRaisesRegex(GITHUB.SourceError, "unavailable"):
                self.prepare()
        self.assertFalse(self.distdir.exists())
        self.assertFalse(self.receipt.exists())

    def test_whole_archive_digest_is_checked_when_declared(self):
        source, data = zipped()
        source["sha256"] = "a" * 64
        self.write_manifest(source)
        with mock.patch.object(GITHUB, "download", side_effect=self.supply(data)):
            with self.assertRaisesRegex(GITHUB.SourceError, "Source size or SHA256"):
                self.prepare()
        self.assertFalse(self.distdir.exists())

    def test_output_names_cannot_collide_with_internal_staging_files(self):
        for name in ("download.asset", "receipt.json"):
            self.write_manifest(direct(name))
            with mock.patch.object(GITHUB, "download", side_effect=self.supply(b"locked tool bytes")):
                self.prepare()
            self.assertEqual((self.distdir / name).read_bytes(), b"locked tool bytes")

    def test_receipt_cannot_overwrite_manifest_or_selected_input(self):
        self.write_manifest(direct())
        for receipt in (self.manifest, self.distdir / "tool.bin"):
            with self.subTest(receipt=receipt), self.assertRaisesRegex(GITHUB.SourceError, "Receipt"):
                GITHUB.prepare(self.manifest, self.distdir, self.cache, receipt)


class ArchiveTest(Fixture):
    def verify(self, source, data):
        path = self.root / "asset"
        path.write_bytes(data)
        stage = self.root / "stage"
        stage.mkdir(exist_ok=True)
        GITHUB.source_files(path, source, stage)

    def test_duplicate_or_absent_selected_members_are_rejected(self):
        source, data = zipped([("bin/tool", b"tool"), ("bin/tool", b"tool")])
        source["files"] = source["files"][:1]
        with self.assertRaisesRegex(GITHUB.SourceError, "exactly one"):
            self.verify(source, data)
        source["files"][0]["path"] = "bin/missing"
        with self.assertRaisesRegex(GITHUB.SourceError, "exactly one"):
            self.verify(source, data)

    def test_symlink_and_encrypted_members_are_rejected(self):
        info = zipfile.ZipInfo("bin/tool")
        info.create_system = 3
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w") as archive:
            archive.writestr(info, b"target")
        source = {"size": len(output.getvalue()), "format": "zip",
                  "files": [entry("tool", b"target", "bin/tool")]}
        with self.assertRaisesRegex(GITHUB.SourceError, "unsupported type"):
            self.verify(source, output.getvalue())
        source, data = zipped([("bin/tool", b"tool")])
        encrypted = bytearray(data)
        for signature, offset in ((b"PK\x03\x04", 6), (b"PK\x01\x02", 8)):
            position = encrypted.index(signature) + offset
            struct.pack_into("<H", encrypted, position, struct.unpack_from("<H", encrypted, position)[0] | 1)
        with self.assertRaisesRegex(GITHUB.SourceError, "unsupported type"):
            self.verify(source, encrypted)

    def test_wrong_declared_member_size_is_rejected_before_decompression(self):
        source, data = zipped()
        source["files"][0]["size"] = 1
        with mock.patch.object(zipfile.ZipFile, "open", side_effect=AssertionError("decompressed")):
            with self.assertRaisesRegex(GITHUB.SourceError, "unsupported type"):
                self.verify(source, data)

    def test_zip_central_directory_allocation_is_bounded_before_opening(self):
        source, data = zipped()
        changed = bytearray(data)
        end = changed.rfind(b"PK\x05\x06")
        struct.pack_into("<L", changed, end + 12, GITHUB.MAX_ZIP_DIRECTORY_BYTES + 1)
        with mock.patch.object(zipfile, "ZipFile", side_effect=AssertionError("allocated directory")):
            with self.assertRaisesRegex(GITHUB.SourceError, "ZIP directory"):
                self.verify(source, changed)

    def test_zip64_locator_is_rejected_even_without_legacy_sentinels(self):
        source, data = zipped()
        end = data.rfind(b"PK\x05\x06")
        record = struct.unpack("<4s4H2LH", data[end:end + 22])
        # ZipFile follows this locator even when the legacy end record has
        # ordinary values. Its ZIP64 values could bypass the directory bound.
        zip64 = struct.pack("<4sQ2H2L4Q", b"PK\x06\x06", 44, 45, 45, 0, 0,
                            record[3], record[4], record[5], record[6])
        locator = struct.pack("<4sLQL", b"PK\x06\x07", 0, end, 1)
        for comment_size in (0, 65535):
            with self.subTest(comment_size=comment_size):
                legacy_end = bytearray(data[end:])
                struct.pack_into("<H", legacy_end, 20, comment_size)
                changed = data[:end] + zip64 + locator + legacy_end + b"x" * comment_size
                # This is a valid ZIP64 archive, not merely malformed bytes.
                with zipfile.ZipFile(io.BytesIO(changed)) as archive:
                    self.assertEqual(archive.read("bin/tool"), b"tool bytes")
                with mock.patch.object(zipfile, "ZipFile", side_effect=AssertionError("allocated directory")):
                    with self.assertRaisesRegex(GITHUB.SourceError, "ZIP64"):
                        self.verify({**source, "size": len(changed)}, changed)

    def test_ordinary_zip_with_maximum_comment_remains_supported(self):
        source, data = zipped()
        end = data.rfind(b"PK\x05\x06")
        changed = bytearray(data)
        struct.pack_into("<H", changed, end + 20, 65535)
        changed.extend(b"x" * 65535)
        self.verify({**source, "size": len(changed)}, changed)
        self.assertEqual((self.root / "stage/tool").read_bytes(), b"tool bytes")

    def test_corrupt_zip_crc_is_rejected(self):
        source, data = zipped([("bin/tool", b"original payload")], zipfile.ZIP_STORED)
        corrupt = data.replace(b"original payload", b"modified payload")
        with self.assertRaisesRegex(GITHUB.SourceError, "ZIP verification"):
            self.verify(source, corrupt)

    def test_nul_aliased_member_is_not_an_exact_path_match(self):
        source, data = zipped([("bin/toolX", b"tool")])
        source["files"][0].update(name="tool", path="bin/tool")
        aliased = data.replace(b"bin/toolX", b"bin/tool\x00")
        with self.assertRaisesRegex(GITHUB.SourceError, "unsupported type"):
            self.verify(source, aliased)

    def test_unselected_paths_are_never_extracted(self):
        source, data = zipped([("bin/tool", b"tool"), ("../outside", b"unselected")])
        source["files"] = source["files"][:1]
        self.verify(source, data)
        self.assertEqual([p.name for p in (self.root / "stage").iterdir()], ["tool"])
        self.assertFalse((self.root / "outside").exists())


class ReleaseAssetAPITest(Fixture):
    API = "https://api.github.com/repos/example/tools/releases/assets/123"
    TOKEN = "fixture_github_token_do_not_log"

    def api_source(self):
        return {**direct(), "url": self.API}

    def test_exact_asset_api_paths_and_redirects_only(self):
        for initial in (True, False):
            GITHUB.validate_url(self.API, initial=initial)
            for url in (self.API + "?download=1", self.API + "#fragment",
                        self.API.replace("/123", "/0"), self.API.replace("/123", "/latest"),
                        self.API.replace("/assets/123", "/tags/v1"),
                        self.API.replace("/example/", "/%65xample/"),
                        self.API.replace("/tools/", "/../"),
                        self.API.replace("api.github.com", "api.github.com.evil.test"),
                        self.API.replace("api.github.com", "user:pass@api.github.com"),
                        self.API.replace("api.github.com", "api.github.com:443")):
                with self.subTest(url=url, initial=initial), self.assertRaises(GITHUB.SourceError):
                    GITHUB.validate_url(url, initial=initial)

    def test_api_authentication_never_follows_redirects(self):
        opener = mock.Mock()
        opener.open.return_value = FakeResponse(b"locked tool bytes", url=self.API)
        with mock.patch.object(GITHUB, "build_opener", return_value=opener):
            GITHUB.download(self.api_source(), self.root / "asset", github_token=self.TOKEN)
        request = opener.open.call_args.args[0]
        self.assertEqual(request.get_header("Accept"), "application/octet-stream")
        self.assertEqual(request.get_header("Authorization"), "Bearer " + self.TOKEN)
        self.assertNotIn("Authorization", request.headers)
        handler = GITHUB.GitHubRedirectHandler()
        for url in ("https://release-assets.githubusercontent.com/asset?signature=fixture",
                    "https://objects.githubusercontent.com/asset?signature=fixture"):
            request = handler.redirect_request(request, None, 302, "Found", {}, url)
            self.assertIsNone(request.get_header("Authorization"))
        with self.assertRaises(GITHUB.SourceError):
            handler.redirect_request(request, None, 302, "Found", {}, "https://other.example/asset")

    def test_no_implicit_credentials_or_authentication_on_non_api_sources(self):
        for source, token in ((self.api_source(), None), (direct(), self.TOKEN)):
            opener = mock.Mock()
            opener.open.return_value = FakeResponse(b"locked tool bytes", url=source["url"])
            with mock.patch.object(GITHUB, "build_opener", return_value=opener), \
                    mock.patch.object(GITHUB.os.environ, "get", side_effect=AssertionError("No token lookup")):
                GITHUB.download(source, self.root / "asset", github_token=token)
            request = opener.open.call_args.args[0]
            self.assertIsNone(request.get_header("Authorization"))
            self.assertEqual(request.get_header("Accept"),
                             "application/octet-stream" if source["url"] == self.API else None)

    def test_api_binary_is_verified_before_publication_without_secret_receipt(self):
        self.write_manifest(self.api_source())
        opener = mock.Mock()
        opener.open.return_value = FakeResponse(b"locked tool bytes", length="17",
            url="https://release-assets.githubusercontent.com/asset?signature=fixture")
        with mock.patch.object(GITHUB, "build_opener", return_value=opener):
            result = GITHUB.prepare(self.manifest, self.distdir, self.cache, self.receipt,
                                    github_token=self.TOKEN)
        self.assertEqual((self.distdir / "tool.bin").read_bytes(), b"locked tool bytes")
        self.assertEqual(result["files"][0]["sha256"], sha(b"locked tool bytes"))
        self.assertNotIn(self.TOKEN, self.receipt.read_text())
        self.assertNotIn("signature=", self.receipt.read_text())
        self.assertEqual(opener.open.call_count, 1)

    def test_api_unverified_response_is_not_published(self):
        self.write_manifest(self.api_source())
        opener = mock.Mock()
        opener.open.return_value = FakeResponse(b"!" * 17, length="17", url=self.API)
        with mock.patch.object(GITHUB, "build_opener", return_value=opener):
            with self.assertRaisesRegex(GITHUB.SourceError, "SHA256"):
                GITHUB.prepare(self.manifest, self.distdir, self.cache, self.receipt,
                               github_token=self.TOKEN)
        self.assertFalse(self.distdir.exists())
        self.assertFalse(self.receipt.exists())

    def test_api_errors_and_invalid_tokens_do_not_leak_or_retry(self):
        for token in ("", "bad\nheader", "non-ascii-\u2603", "a" * 4097):
            opener = mock.Mock()
            with mock.patch.object(GITHUB, "build_opener", return_value=opener):
                with self.assertRaises(GITHUB.SourceError) as caught:
                    GITHUB.download(self.api_source(), self.root / "asset", github_token=token)
            self.assertNotIn(token or "bad header", str(caught.exception))
            opener.open.assert_not_called()
        opener = mock.Mock()
        opener.open.side_effect = HTTPError(self.API, 403, self.TOKEN, {}, None)
        with mock.patch.object(GITHUB, "build_opener", return_value=opener):
            with self.assertRaises(GITHUB.SourceError) as caught:
                GITHUB.download(self.api_source(), self.root / "asset", github_token=self.TOKEN)
        self.assertNotIn(self.TOKEN, str(caught.exception))
        self.assertEqual(opener.open.call_count, 1)

    def cli(self, *args):
        return ["--manifest", str(self.manifest), "--distdir", str(self.distdir),
                "--cache-dir", str(self.cache), "--receipt", str(self.receipt), *args]

    def test_cli_reads_only_explicit_token_environment(self):
        with mock.patch.object(GITHUB.os.environ, "get", wraps=GITHUB.os.environ.get) as lookup, \
                mock.patch.object(GITHUB, "prepare") as prepare:
            self.assertEqual(GITHUB.main(self.cli()), 0)
        self.assertFalse(any(call.args[0] in ("GITHUB_TOKEN", "GH_TOKEN") for call in lookup.call_args_list))
        self.assertIsNone(prepare.call_args.kwargs["github_token"])
        with mock.patch.dict(GITHUB.os.environ, {"GITHUB_TOKEN": self.TOKEN}), \
                mock.patch.object(GITHUB, "prepare") as prepare:
            self.assertEqual(GITHUB.main(self.cli("--github-token-env", "GITHUB_TOKEN")), 0)
        self.assertEqual(prepare.call_args.kwargs["github_token"], self.TOKEN)

    def test_cli_invalid_or_missing_token_fails_before_preparation(self):
        for name, value in (("BAD=NAME", self.TOKEN), ("GITHUB_TOKEN", None),
                            ("GITHUB_TOKEN", ""), ("GITHUB_TOKEN", "bad\rheader")):
            env = {} if value is None or name == "BAD=NAME" else {name: value}
            errors = io.StringIO()
            with mock.patch.dict(GITHUB.os.environ, env, clear=True), \
                    mock.patch.object(GITHUB, "prepare") as prepare, \
                    mock.patch.object(GITHUB.sys, "stderr", errors):
                self.assertEqual(GITHUB.main(self.cli("--github-token-env", name)), 1)
            prepare.assert_not_called()
            if value:
                self.assertNotIn(value, errors.getvalue())


if __name__ == "__main__":
    unittest.main()
