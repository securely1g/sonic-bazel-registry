"""Exercise repository HTTP retry limits and integrity checks with actual Bazel."""

from __future__ import annotations

import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest


SPEC = importlib.util.spec_from_file_location(
    "registry_ci_http_integration", Path(__file__).resolve().parents[1] / "registry_ci.py"
)
assert SPEC is not None and SPEC.loader is not None
registry_ci = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = registry_ci
SPEC.loader.exec_module(registry_ci)


@unittest.skipUnless(os.environ.get("REGISTRY_CI_TEST_BAZEL"),
                     "set REGISTRY_CI_TEST_BAZEL to run the real Bazel HTTP retry fixture")
class BazelHttpRetryIntegrationTest(unittest.TestCase):
    def test_transient_503_recovery_preserves_source_integrity(self):
        original = b"verified repository fixture\n"
        checksum = hashlib.sha256(original).hexdigest()
        for case, flags, transient_errors, corrupt, succeeds, expected_requests in (
                ("default", [], 8, False, False, 8),
                ("recovered", registry_ci.HTTP_DOWNLOAD_FLAGS, 8, False, True, 9),
                ("corrupt", registry_ci.HTTP_DOWNLOAD_FLAGS, 0, True, False, 1)):
            with self.subTest(case=case), tempfile.TemporaryDirectory(prefix="registry-http-retry-") as temporary:
                work = Path(temporary)
                consumer, artifacts, cache = work / "consumer", work / "artifacts", work / "cache"
                for directory in (consumer, artifacts, cache):
                    directory.mkdir()
                self.assertEqual(list(cache.iterdir()), [])
                requests = []

                class Source(BaseHTTPRequestHandler):
                    def do_GET(self):
                        status = 503 if len(requests) < transient_errors else 200
                        requests.append({"path": self.path, "status": status, "time": time.monotonic()})
                        body = (b"temporary failure\n" if status == 503 else
                                b"changed source bytes\n" if corrupt else original)
                        self.send_response(status)
                        self.send_header("Content-Length", str(len(body)))
                        self.end_headers()
                        self.wfile.write(body)

                    def log_message(self, *_args):
                        pass

                server = ThreadingHTTPServer(("127.0.0.1", 0), Source)
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                try:
                    url = f"http://127.0.0.1:{server.server_port}/source"
                    (consumer / "MODULE.bazel").write_text(
                        'module(name = "http_retry_consumer")\n'
                        'http_file = use_repo_rule("@bazel_tools//tools/build_defs/repo:http.bzl", "http_file")\n'
                        f'http_file(name = "source", urls = [{url!r}], sha256 = {checksum!r})\n')
                    (consumer / "BUILD.bazel").write_text("")
                    command = [os.environ["REGISTRY_CI_TEST_BAZEL"], "--batch", "--ignore_all_rc_files",
                               "--output_user_root=" + str(work / "bazel"), "fetch", "--repo=@source",
                               "--repository_cache=" + str(cache), "--lockfile_mode=off", *flags]
                    (artifacts / "command.json").write_text(json.dumps(command, indent=2) + "\n")
                    log_path = artifacts / "fetch.log"
                    with log_path.open("w") as log:
                        result = subprocess.run(command, cwd=consumer, stdout=log,
                                                stderr=subprocess.STDOUT, timeout=120)
                    transcript = log_path.read_text()
                    self.assertEqual(len(requests), expected_requests, transcript)
                    self.assertEqual({request["path"] for request in requests}, {"/source"})
                    archive = cache / "content_addressable/sha256" / checksum / "file"
                    if succeeds:
                        self.assertEqual(result.returncode, 0, transcript)
                        self.assertEqual(archive.read_bytes(), original)
                    else:
                        self.assertNotEqual(result.returncode, 0, transcript)
                        self.assertFalse(archive.exists(), "Unverified bytes entered the repository cache")
                        self.assertIn("Checksum" if corrupt else "503", transcript)
                    (artifacts / "result.json").write_text(json.dumps({
                        "case": case, "status": "passed", "requests": len(requests),
                        "exit_code": result.returncode, "expected_sha256": checksum,
                        "empty_repository_cache": True,
                    }, indent=2) + "\n")
                finally:
                    server.shutdown()
                    server.server_close()
                    thread.join(timeout=5)
                    (artifacts / "requests.json").write_text(json.dumps(requests, indent=2) + "\n")
                    destination = os.environ.get("REGISTRY_CI_TEST_ARTIFACTS")
                    if destination:
                        shutil.copytree(artifacts, Path(destination) / (work.name + "-" + case))


if __name__ == "__main__":
    unittest.main()
