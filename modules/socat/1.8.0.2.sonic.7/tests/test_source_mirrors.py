"""Check the unpublished socat candidate's pinned source download contract."""

import ast
import base64
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import unittest


ENTRY = Path(__file__).resolve().parents[1]
MIRROR = "https://packages.trafficmanager.net/public/debian/"
SNAPSHOT = (
    "https://snapshot.debian.org/archive/debian/"
    "20241222T205329Z/pool/main/s/socat/"
)
ARCHIVES = {
    "upstream": (
        "socat_1.8.0.2.orig.tar.bz2",
        "adc07a9c2723527cf6568d2fb96559794cf9c254a4bc2edd36f7f3789e9f7625",
        "tar.bz2",
    ),
    "debian": (
        "socat_1.8.0.2-1.debian.tar.xz",
        "04b361cd91884eda6ca9fe2890ca83a6abe73dd8ce75fe9927b2d8443af36123",
        "tar.xz",
    ),
}


class SourceMirrorsTest(unittest.TestCase):
    def test_module_uses_ordered_candidates_and_original_hashes(self):
        module = ast.parse((ENTRY / "MODULE.bazel").read_text())
        calls = [
            node for node in ast.walk(module)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "socat_source"
        ]
        self.assertEqual(len(calls), 1)
        values = {item.arg: ast.literal_eval(item.value) for item in calls[0].keywords}
        for name, (filename, sha256, _) in ARCHIVES.items():
            with self.subTest(archive=name):
                self.assertEqual(values[f"{name}_urls"], [MIRROR + filename, SNAPSHOT + filename])
                self.assertEqual(values[f"{name}_sha256"], sha256)

    def test_registry_root_archive_uses_the_same_candidates_and_hash(self):
        source = json.loads((ENTRY / "source.json").read_text())
        filename, sha256, _ = ARCHIVES["upstream"]
        self.assertEqual(source["url"], MIRROR + filename)
        self.assertEqual(source["mirror_urls"], [SNAPSHOT + filename])
        self.assertEqual(
            source["integrity"],
            "sha256-" + base64.b64encode(bytes.fromhex(sha256)).decode("ascii"),
        )
        self.assertEqual(source["strip_prefix"], "socat-1.8.0.2")

    def test_repository_rule_passes_url_lists_hashes_and_explicit_formats(self):
        source = ast.parse((ENTRY / "overlay/bazel/source.bzl").read_text())
        calls = [
            node for node in ast.walk(source)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "download_and_extract"
        ]
        self.assertEqual(len(calls), 2)
        for call, (name, (_, _, archive_type)) in zip(calls, ARCHIVES.items()):
            with self.subTest(archive=name):
                values = {item.arg: item.value for item in call.keywords}
                self.assertEqual(ast.unparse(values["url"]), f"ctx.attr.{name}_urls")
                self.assertEqual(ast.unparse(values["sha256"]), f"ctx.attr.{name}_sha256")
                self.assertEqual(ast.literal_eval(values["type"]), archive_type)

    def test_overlay_integrities_and_full_validation_matrix_are_preserved(self):
        source = json.loads((ENTRY / "source.json").read_text())
        for filename, integrity in source["overlay"].items():
            with self.subTest(overlay=filename):
                actual = hashlib.sha256((ENTRY / "overlay" / filename).read_bytes()).digest()
                self.assertEqual(integrity, "sha256-" + base64.b64encode(actual).decode("ascii"))
        published = ENTRY.parent / "1.8.0.2.sonic.6"
        self.assertEqual(
            json.loads((ENTRY / "presubmit.json").read_text()),
            json.loads((published / "presubmit.json").read_text()),
        )
        for filename in (
            "BUILD.bazel", "bazel/socat.BUILD.bazel", "socat_package_test.py",
            "runtime_packages.md", "bazel/0001-enable-readline.patch",
            "bazel/0002-compiler-metadata.patch", "bazel/0003-procan-namespace-nul.patch",
        ):
            with self.subTest(preserved=filename):
                self.assertEqual(
                    (ENTRY / "overlay" / filename).read_bytes(),
                    (published / "overlay" / filename).read_bytes(),
                )


@unittest.skipUnless(
    os.environ.get("REGISTRY_CI_TEST_BAZEL") and os.environ.get("SOCAT_SOURCE_ARCHIVES"),
    "set REGISTRY_CI_TEST_BAZEL and SOCAT_SOURCE_ARCHIVES for real Bazel fetch tests",
)
class SourceFetchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix="socat-source-fetch-")
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.root = Path(cls.temporary.name)
        cls.archives = {}
        for filename, sha256, _ in ARCHIVES.values():
            data = (Path(os.environ["SOCAT_SOURCE_ARCHIVES"]) / filename).read_bytes()
            if hashlib.sha256(data).hexdigest() != sha256:
                raise ValueError("Source fixture does not match the pinned hash: " + filename)
            cls.archives[filename] = data

    def fetch(self, mode):
        work = self.root / mode
        work.mkdir()
        shutil.copytree(ENTRY / "overlay/bazel", work / "bazel")
        (work / "BUILD.bazel").write_text('exports_files(glob(["bazel/**"]))\n')
        module = ast.parse((ENTRY / "MODULE.bazel").read_text())
        arguments = next(node for node in ast.walk(module)
                         if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                         and node.func.id == "socat_source")
        values = {item.arg: ast.literal_eval(item.value) for item in arguments.keywords}
        source = json.loads((ENTRY / "source.json").read_text())
        workspace = (
            'module(name = "socat_source_fetch_test")\n'
            'http_archive = use_repo_rule("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")\n'
            'socat_source = use_repo_rule("//:bazel/source.bzl", "socat_source")\n'
            'http_archive(name = "socat_root", urls = '
            + repr([source["url"], *source["mirror_urls"]])
            + ', integrity = ' + repr(source["integrity"])
            + ', strip_prefix = "socat-1.8.0.2", type = "tar.bz2", '
            + 'build_file_content = \'exports_files(["README"])\\n\')\n'
            + 'socat_source(' + ', '.join(key + '=' + repr(value) for key, value in values.items()) + ')\n'
        )
        (work / "MODULE.bazel").write_text(workspace)
        requests = []
        archives = self.archives

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                _, location, filename = self.path.split("/", 2)
                requests.append((location, filename))
                if location == "mirror" and mode == "missing":
                    self.send_error(404)
                    return
                data = archives[filename]
                if mode == "all-corrupt" or (location == "mirror" and mode == "corrupt"):
                    data = b"corrupt archive fixture"
                self.send_response(200)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *_):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        try:
            config = work / "downloader.cfg"
            prefix = f"http://127.0.0.1:{server.server_port}"
            config.write_text(
                r"rewrite packages\.trafficmanager\.net/public/debian/(.*) "
                + prefix + "/mirror/$1\n"
                + r"rewrite snapshot\.debian\.org/archive/debian/20241222T205329Z/pool/main/s/socat/(.*) "
                + prefix + "/upstream/$1\n")
            command = [
                os.environ["REGISTRY_CI_TEST_BAZEL"], "--batch", "--ignore_all_rc_files",
                "--output_user_root=" + str(self.root / "bazel-user"),
                "--output_base=" + str(work / "output"),
                "fetch",
                "--incompatible_autoload_externally=", "--repository_cache=",
                "--repo=@socat_root", "--repo=@socat_source",
            ]
            if mode != "live":
                command.append("--experimental_downloader_config=" + str(config))
            result = subprocess.run(
                command, cwd=work, capture_output=True, text=True, timeout=180)
        finally:
            server.shutdown()
            thread.join()
            server.server_close()
        if mode == "all-corrupt":
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("Checksum", result.stderr)
        else:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            sources = list((work / "output/external").glob("*+socat_source/socat.c"))
            self.assertEqual(len(sources), 1, result.stdout + result.stderr)
            prepared = sources[0].parent
            self.assertIn("libreadline-dev", (prepared / "debian/control").read_text())
        if mode != "live":
            self.assertTrue(any(location == "mirror" for location, _ in requests), requests)
            if mode in ("missing", "corrupt", "all-corrupt"):
                self.assertTrue(any(location == "upstream" for location, _ in requests), requests)
            else:
                self.assertFalse(any(location == "upstream" for location, _ in requests), requests)

    def test_live_mirror_downloads_and_source_patches(self):
        self.fetch("live")

    def test_mirror_success_does_not_request_upstream(self):
        self.fetch("success")

    def test_missing_mirror_falls_back_to_upstream(self):
        self.fetch("missing")

    def test_corrupt_mirror_falls_back_with_original_checksum(self):
        self.fetch("corrupt")

    def test_all_corrupt_candidates_are_rejected(self):
        self.fetch("all-corrupt")


if __name__ == "__main__":
    unittest.main()
