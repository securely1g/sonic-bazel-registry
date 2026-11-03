"""Fetch the unchanged BCR pigz recipe with Bazel, including a corrupt mirror."""
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
    def test_scope_is_limited_to_this_pr_and_rejects_module_changes(self):
        workflow = (ROOT / ".github/workflows/registry-ci.yml").read_text()
        script = workflow.split("          python3 - <<'PY'\n", 1)[1].split("          PY\n", 1)[0]
        script = "\n".join(line[10:] for line in script.splitlines())
        for branch, repository, changed, expected in (
            ("codex/pigz-source-mirror", "securely1g/sonic-bazel-registry", "ci/source_mirrors.cfg", []),
            ("codex/pigz-source-mirror", "securely1g/sonic-bazel-registry", "modules/pigz/source.json", None),
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
                        if expected is None:
                            with self.assertRaises(SystemExit):
                                exec(compile(script, "registry-ci-workflow", "exec"), {})
                            self.assertFalse(output.exists())
                            continue
                        exec(compile(script, "registry-ci-workflow", "exec"), {})
                    line = output.read_text().splitlines()[0]
                    self.assertEqual(json.loads(line.removeprefix("matrix="))["include"], expected)


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


if __name__ == "__main__":
    unittest.main()
