"""Verify pigz and Debian snapshot mirrors with real Bazel and pinned hashes."""
from __future__ import annotations

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
from unittest import mock
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[2]
PIGZ_SHA256 = "eb872b4f0e1f0ebe59c9f7bd8c506c4204893ba6a8492de31df416f0d5170fd0"
PIGZ_MODULE = "https://bcr.bazel.build/modules/pigz/2.8.bcr.2/MODULE.bazel"


class SourceMirrorWorkflowScopeTest(unittest.TestCase):
    def test_matrix_is_preserved_for_every_branch(self):
        workflow = (ROOT / ".github/workflows/registry-ci.yml").read_text()
        script = workflow.split("          python3 - <<'PY'\n", 1)[1].split("          PY\n", 1)[0]
        script = "\n".join(line[10:] for line in script.splitlines())
        for branch, repository, changed, expected in (
            ("codex/pigz-source-mirror", "securely1g/sonic-bazel-registry", "ci/source_mirrors.cfg", [{"module": "original"}]),
            ("codex/pigz-source-mirror", "securely1g/sonic-bazel-registry", "modules/pigz/source.json", [{"module": "original"}]),
            ("other", "securely1g/sonic-bazel-registry", "ci/source_mirrors.cfg", [{"module": "original"}]),
            ("codex/pigz-source-mirror", "another/fork", "ci/source_mirrors.cfg", [{"module": "original"}]),
        ):
            with self.subTest(branch=branch, repository=repository, changed=changed):
                with tempfile.TemporaryDirectory(prefix="mirror-workflow-") as temporary:
                    output = Path(temporary) / "output"
                    env = {"EVENT_NAME": "pull_request", "HEAD_REF": branch,
                           "HEAD_REPOSITORY": repository, "BASE_SHA": "a" * 40,
                           "HEAD_SHA": "b" * 40, "GITHUB_OUTPUT": str(output)}
                    with mock.patch.dict(os.environ, env), \
                            mock.patch.object(Path, "read_text", return_value='{"include":[{"module":"original"}]}'), \
                            mock.patch.object(subprocess, "check_output", return_value=changed + "\n"):
                        exec(compile(script, "registry-ci-workflow", "exec"), {})
                    line = output.read_text().splitlines()[0]
                    self.assertEqual(json.loads(line.removeprefix("matrix="))["include"], expected)
                    self.assertIn("has_jobs=true", output.read_text().splitlines())


@unittest.skipUnless(os.environ.get("REGISTRY_CI_TEST_BAZEL"),
                     "set REGISTRY_CI_TEST_BAZEL to exercise real Bazel downloads")
class SourceMirrorIntegrationTest(unittest.TestCase):
    def test_original_bcr_archive_and_patches_with_empty_cache(self):
        self.exercise_mirror(corrupt=False)

    def test_mirror_cannot_replace_original_bcr_archive(self):
        self.exercise_mirror(corrupt=True)

    def exercise_mirror(self, *, corrupt):
        with tempfile.TemporaryDirectory(prefix="registry-source-mirror-") as temporary:
            work = Path(temporary)
            consumer = work / "consumer"
            consumer.mkdir()
            artifacts = work / "artifacts"
            artifacts.mkdir()
            (consumer / "MODULE.bazel").write_text(
                'module(name = "pigz_mirror_consumer")\n'
                'bazel_dep(name = "pigz", version = "2.8.bcr.2")\n')
            (consumer / "BUILD.bazel").write_text("")
            config = ROOT / "ci/source_mirrors.cfg"
            server = None
            requests = []
            if corrupt:
                class WrongArchive(BaseHTTPRequestHandler):
                    def do_GET(self):
                        requests.append(self.path)
                        payload = b"not the original pigz source archive\n"
                        self.send_response(200)
                        self.send_header("Content-Length", str(len(payload)))
                        self.end_headers()
                        self.wfile.write(payload)

                    def log_message(self, *_args):
                        pass

                server = ThreadingHTTPServer(("127.0.0.1", 0), WrongArchive)
                threading.Thread(target=server.serve_forever, daemon=True).start()
                config = work / "corrupt.cfg"
                config.write_text((ROOT / "ci/source_mirrors.cfg").read_text().replace(
                    "https://distfiles.macports.org/pigz/pigz-2.8.tar.gz",
                    f"http://127.0.0.1:{server.server_port}/pigz-2.8.tar.gz"))
            cache = work / "repository-cache"
            cache.mkdir()
            self.assertEqual(list(cache.iterdir()), [])
            prefix = [os.environ["REGISTRY_CI_TEST_BAZEL"], "--batch", "--ignore_all_rc_files",
                      "--output_user_root=" + str(work / "bazel"),
                      "--output_base=" + str(work / "output")]
            command = [*prefix, "fetch", "--repo=@pigz", "--registry=https://bcr.bazel.build/",
                       "--repository_cache=" + str(cache), "--lockfile_mode=update",
                       "--experimental_downloader_config=" + str(config)]
            try:
                (artifacts / "command.json").write_text(json.dumps(command, indent=2) + "\n")
                with (artifacts / "fetch.log").open("w") as log:
                    result = subprocess.run(command, cwd=consumer, stdout=log,
                                            stderr=subprocess.STDOUT, timeout=300)
                transcript = (artifacts / "fetch.log").read_text()
                archive = cache / "content_addressable/sha256" / PIGZ_SHA256 / "file"
                if corrupt:
                    self.assertNotEqual(result.returncode, 0, transcript)
                    self.assertIn("Checksum", transcript)
                    self.assertTrue(requests, "Bazel did not request the corrupt mirror")
                    self.assertEqual(set(requests), {"/pigz-2.8.tar.gz"})
                    self.assertFalse(archive.exists(), "Corrupt archive entered the verified cache")
                else:
                    self.assertEqual(result.returncode, 0, transcript)
                    self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(), PIGZ_SHA256)
                    fetched = list((work / "output/external").glob("pigz*/MODULE.bazel"))
                    self.assertEqual(len(fetched), 1, fetched)
                    with urlopen(PIGZ_MODULE, timeout=60) as response:
                        expected_module = response.read()
                    self.assertEqual(fetched[0].read_bytes(), expected_module)
                    # Successful extraction applies all unchanged BCR patches,
                    # including the upstream BUILD and module declarations.
                    self.assertTrue((fetched[0].parent / "BUILD.bazel").is_file())
                    shutil.copy2(fetched[0], artifacts / "fetched.MODULE.bazel")
                    shutil.copy2(consumer / "MODULE.bazel.lock", artifacts / "MODULE.bazel.lock")
                (artifacts / "result.json").write_text(json.dumps({
                    "corrupt_mirror": corrupt, "status": "passed",
                    "module": "pigz@2.8.bcr.2", "original_archive_sha256": PIGZ_SHA256,
                    "empty_repository_cache": True, "distdir": None,
                    "package_actions_executed": False,
                }, indent=2) + "\n")
            finally:
                if server:
                    server.shutdown()
                    server.server_close()
                destination = os.environ.get("REGISTRY_CI_TEST_ARTIFACTS")
                if destination:
                    shutil.copytree(artifacts, Path(destination) / work.name)


@unittest.skipUnless(os.environ.get("REGISTRY_CI_TEST_BAZEL"),
                     "set REGISTRY_CI_TEST_BAZEL to exercise real Bazel downloads")
class DebianSnapshotMirrorIntegrationTest(unittest.TestCase):
    def test_snapshot_archive_security_and_index_paths(self):
        self.exercise_snapshot("mirror")

    def test_original_snapshot_fallback(self):
        self.exercise_snapshot("fallback")

    def test_snapshot_checksum_rejection(self):
        self.exercise_snapshot("corrupt")

    def exercise_snapshot(self, scenario):
        paths = {
            "ordinary": "archive/debian/20260727T143429Z/pool/main/p/package/package_1_amd64.deb",
            "security": "archive/debian-security/20260727T143429Z/pool/updates/main/p/package/package_1_arm64.deb",
            "index": "archive/debian/20260727T143429Z/dists/trixie/main/binary-amd64/Packages.xz",
        }
        # Distinct fixture payloads prevent one repository-cache hit from
        # concealing whether a different URL is routed correctly.
        payloads = {path: ("snapshot routing fixture: " + path).encode() for path in paths.values()}
        requests = []

        class SnapshotEndpoint(BaseHTTPRequestHandler):
            def do_GET(self):
                endpoint, path = self.path.lstrip("/").split("/", 1)
                requests.append((endpoint, path))
                if path not in payloads:
                    self.send_error(404)
                    return
                if scenario == "fallback" and endpoint == "mirror":
                    self.send_error(404)
                    return
                payload = b"incorrect snapshot bytes" if scenario == "corrupt" else payloads[path]
                self.send_response(200)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *_args):
                pass

        with tempfile.TemporaryDirectory(prefix="registry-snapshot-mirror-") as temporary:
            work = Path(temporary)
            artifacts = work / "artifacts"
            artifacts.mkdir()
            server = ThreadingHTTPServer(("127.0.0.1", 0), SnapshotEndpoint)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            config = (ROOT / "ci/source_mirrors.cfg").read_text()
            config = config.replace("https://snapshot-cloudflare.debian.org/$1",
                                    f"http://127.0.0.1:{server.server_port}/mirror/$1")
            config = config.replace("https://snapshot.debian.org/$1",
                                    f"http://127.0.0.1:{server.server_port}/original/$1")
            (work / "downloader.cfg").write_text(config)
            (work / "archive.bzl").write_text(
                'def _impl(ctx):\n'
                '    ctx.download(ctx.attr.url, output = "payload", sha256 = ctx.attr.sha256)\n'
                '    ctx.file("BUILD.bazel", \'exports_files(["payload"])\\n\')\n'
                'archive = repository_rule(implementation = _impl, attrs = {"url": attr.string(), "sha256": attr.string()})\n')
            workspace = 'workspace(name = "snapshot_routing_test")\nload("//:archive.bzl", "archive")\n'
            for name, path in paths.items():
                workspace += f'archive(name = "{name}", url = "https://snapshot.debian.org/{path}", sha256 = "{hashlib.sha256(payloads[path]).hexdigest()}")\n'
            (work / "WORKSPACE.bazel").write_text(workspace)
            (work / "BUILD.bazel").write_text('exports_files(["archive.bzl"])\n')
            for name in ("downloader.cfg", "WORKSPACE.bazel", "BUILD.bazel", "archive.bzl"):
                shutil.copy2(work / name, artifacts / name)
            cache = work / "repository-cache"
            cache.mkdir()
            self.assertEqual(list(cache.iterdir()), [])
            command = [os.environ["REGISTRY_CI_TEST_BAZEL"], "--batch", "--ignore_all_rc_files",
                       "--output_user_root=" + str(work / "bazel"),
                       "--output_base=" + str(work / "output"), "fetch",
                       "--enable_bzlmod=false", "--enable_workspace=true",
                       "--repository_cache=" + str(cache),
                       "--experimental_downloader_config=" + str(work / "downloader.cfg"),
                       *[f"@{name}//:payload" for name in paths]]
            try:
                (artifacts / "command.json").write_text(json.dumps(command, indent=2) + "\n")
                with (artifacts / "fetch.log").open("w") as log:
                    result = subprocess.run(command, cwd=work, stdout=log,
                                            stderr=subprocess.STDOUT, timeout=120)
                transcript = (artifacts / "fetch.log").read_text()
                if scenario == "corrupt":
                    self.assertNotEqual(result.returncode, 0, transcript)
                    self.assertIn("Checksum", transcript)
                    self.assertTrue(requests, "No snapshot requests were made")
                    for payload in payloads.values():
                        self.assertFalse((cache / "content_addressable/sha256" /
                                          hashlib.sha256(payload).hexdigest() / "file").exists())
                else:
                    self.assertEqual(result.returncode, 0, transcript)
                    for name, path in paths.items():
                        self.assertEqual((work / "output/external" / name / "payload").read_bytes(), payloads[path])
                        self.assertIn(("mirror", path), requests)
                        if scenario == "fallback":
                            self.assertLess(requests.index(("mirror", path)), requests.index(("original", path)))
                        else:
                            self.assertNotIn(("original", path), requests)
                (artifacts / "result.json").write_text(json.dumps({
                    "scenario": scenario, "requests": requests, "result": "passed",
                    "source_config_sha256": hashlib.sha256((ROOT / "ci/source_mirrors.cfg").read_bytes()).hexdigest(),
                    "controlled_endpoints": True, "empty_repository_cache": True,
                    "package_actions_executed": False,
                }, indent=2) + "\n")
            finally:
                server.shutdown()
                server.server_close()
                destination = os.environ.get("REGISTRY_CI_TEST_ARTIFACTS")
                if destination:
                    shutil.copytree(artifacts, Path(destination) / work.name)


if __name__ == "__main__":
    unittest.main()
