"""Exercise pinned Debian URL routing and Bazel's unchanged payload checksum."""
from __future__ import annotations

import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import threading
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
BRANCH = "codex/registry-debian-pool-transport"
# Exact input from source PR82's failed declared-build-tools attempt2.
TOMLI_URL = "https://snapshot.debian.org/archive/debian/20260727T143429Z/pool/main/p/python-tomli/python3-tomli_2.2.1-2+b1_amd64.deb"
TOMLI_SHA256 = "57d5ee29234ba145e298a36e4530ff261bf2e706e9df95d08cfeee1d7e8362a9"


def routed_urls(url):
    """Evaluate the checked-in rewrite data with full URL matching."""
    result = []
    for line in (ROOT / "ci/source_mirrors.cfg").read_text().splitlines():
        if not line.startswith("rewrite "):
            continue
        _, pattern, replacement = line.split()
        match = re.fullmatch(pattern, url.removeprefix("https://"))
        if match:
            result.append(re.sub(r"\$(\d+)", lambda m: match.group(int(m[1])), replacement))
    return result or [url]


class DebianPoolRoutingTest(unittest.TestCase):
    def test_actual_bookworm_failure_uses_verified_content_before_prior_routes(self):
        # Registry226 run41895100402 retained the actual failed lock. The
        # repository still requires SHA256 ea265b1dff21ab2e4b22b38097031f8d63fb940ecb89427659655598860efc0f;
        # this SHA1-derived URL changes delivery, not the checksum policy.
        original = "https://snapshot.debian.org/archive/debian-security/20260726T121236Z/pool/updates/main/l/linux/linux-libc-dev_6.1.177-1_amd64.deb"
        self.assertEqual(routed_urls(original), [
            "https://snapshot.debian.org/file/aed472fca7f9b98fdb7103b974db264cb60c2248",
            "https://deb.debian.org/debian-security/pool/updates/main/l/linux/linux-libc-dev_6.1.177-1_amd64.deb",
            original,
        ])

    def test_historical_rule_cannot_redirect_other_package_identities(self):
        original = "https://snapshot.debian.org/archive/debian-security/20260726T121236Z/pool/updates/main/l/linux/linux-libc-dev_6.1.177-1_amd64.deb"
        for changed in (
            original.replace("6.1.177-1", "6.1.178-1"),
            original.replace("_amd64", "_arm64"),
            original.replace("20260726T121236Z", "20260725T121236Z"),
            original.replace("linux-libc-dev", "linux-headers"),
        ):
            with self.subTest(url=changed):
                relative = changed.split("/pool/", 1)[1]
                self.assertEqual(routed_urls(changed), [
                    "https://deb.debian.org/debian-security/pool/" + relative,
                    changed,
                ])
        for unchanged in (original + "?alternate=1", original + "#fragment",
                          original.replace("snapshot.debian.org", "other.example")):
            with self.subTest(url=unchanged):
                self.assertEqual(routed_urls(unchanged), [unchanged])

    def test_actual_failed_payloads_keep_original_snapshot_second(self):
        for original in [TOMLI_URL,
            "https://snapshot.debian.org/archive/debian/20260727T143429Z/pool/main/t/thrift/libthrift-dev_0.19.0-4+b1_armhf.deb",
            "https://snapshot.debian.org/archive/debian/20260727T143429Z/pool/main/g/gmp/libgmp-dev_6.3.0+dfsg-3_armhf.deb",
            "https://snapshot.debian.org/archive/debian/20260727T143429Z/pool/main/g/glibc/libc6-dbg_2.41-12+deb13u3_amd64.deb",
            "https://snapshot.debian.org/archive/debian-security/20260726T121236Z/pool/updates/main/o/openssl/libssl-dev_3.5.6-1~deb13u2_armhf.deb"]:
            with self.subTest(url=original):
                archive, relative = original.split("/archive/", 1)[1].split("/", 1)
                pool = relative.split("/pool/", 1)[1]
                self.assertEqual(routed_urls(original),
                    [f"https://deb.debian.org/{archive}/pool/{pool}", original])

    def test_indexes_sources_and_other_hosts_are_unchanged(self):
        for url in [
            "https://snapshot.debian.org/archive/debian/20260727T143429Z/dists/trixie/Release",
            "https://snapshot.debian.org/archive/debian-security/20260726T121236Z/dists/trixie-security/main/binary-amd64/Packages.xz",
            TOMLI_URL.replace(".deb", ".dsc"), TOMLI_URL.replace(".deb", ".orig.tar.gz"),
            TOMLI_URL.replace("snapshot.debian.org", "other.example"),
            TOMLI_URL + "?alternate=1", TOMLI_URL + "#fragment",
            TOMLI_URL.replace("20260727T143429Z", "latest"),
        ]:
            with self.subTest(url=url):
                self.assertEqual(routed_urls(url), [url])

    def test_existing_pigz_mirror_is_preserved(self):
        self.assertEqual(routed_urls("https://zlib.net/pigz/pigz-2.8.tar.gz"),
                         ["https://distfiles.macports.org/pigz/pigz-2.8.tar.gz"])
        original = "https://zlib.net/pigz/pigz-2.9.tar.gz"
        self.assertEqual(routed_urls(original), [original])

    def test_exact_workflow_scope_and_rejected_changes(self):
        workflow = (ROOT / ".github/workflows/registry-ci.yml").read_text()
        script = workflow.split("          python3 - <<'PY'\n", 1)[1].split("          PY\n", 1)[0]
        script = "\n".join(line[10:] for line in script.splitlines())
        original = {"include": [{"module": "original"}]}
        cases = [
            ("pull_request", BRANCH, "securely1g/sonic-bazel-registry", "ci/source_mirrors.cfg", []),
            ("pull_request", BRANCH, "securely1g/sonic-bazel-registry", "ci/registry_ci.py", None),
            ("pull_request", BRANCH, "securely1g/sonic-bazel-registry", "modules/pigz/metadata.json", None),
            ("pull_request", BRANCH, "securely1g/sonic-bazel-registry", "", None),
            ("pull_request", BRANCH + "-other", "securely1g/sonic-bazel-registry", "ci/source_mirrors.cfg", original["include"]),
            ("pull_request", BRANCH, "another/fork", "ci/source_mirrors.cfg", original["include"]),
            ("push", BRANCH, "securely1g/sonic-bazel-registry", "ci/source_mirrors.cfg", original["include"]),
            ("workflow_dispatch", BRANCH, "securely1g/sonic-bazel-registry", "ci/source_mirrors.cfg", original["include"]),
        ]
        for event, branch, repository, changed, expected in cases:
            with self.subTest(event=event, branch=branch, repository=repository, changed=changed):
                with tempfile.TemporaryDirectory() as temporary:
                    output = Path(temporary) / "output"
                    env = {"EVENT_NAME": event, "HEAD_REF": branch, "HEAD_REPOSITORY": repository,
                           "BASE_SHA": "a" * 40, "HEAD_SHA": "b" * 40, "GITHUB_OUTPUT": str(output)}
                    with mock.patch.dict(os.environ, env), \
                         mock.patch.object(Path, "read_text", return_value=json.dumps(original)), \
                         mock.patch.object(subprocess, "check_output", return_value=changed + "\n"):
                        if expected is None:
                            with self.assertRaises(SystemExit):
                                exec(compile(script, "registry-workflow", "exec"), {})
                            self.assertFalse(output.exists())
                            continue
                        exec(compile(script, "registry-workflow", "exec"), {})
                    actual = json.loads(output.read_text().splitlines()[0].removeprefix("matrix="))
                    self.assertEqual(actual["include"], expected)


@unittest.skipUnless(os.environ.get("REGISTRY_CI_TEST_BAZEL"),
                     "set REGISTRY_CI_TEST_BAZEL to exercise real Bazel downloads")
class DebianPoolIntegrationTest(unittest.TestCase):
    def test_actual_locked_payload_through_production_config(self):
        self.fetch_payload(corrupt=False)

    def test_corrupt_payload_cannot_enter_verified_cache(self):
        self.fetch_payload(corrupt=True)

    def fetch_payload(self, *, corrupt):
        with tempfile.TemporaryDirectory(prefix="registry-debian-pool-") as temporary:
            work = Path(temporary)
            consumer, artifacts, cache = work / "consumer", work / "artifacts", work / "cache"
            for directory in [consumer, artifacts, cache]:
                directory.mkdir()
            (consumer / "MODULE.bazel").write_text(
                'module(name = "debian_transport_check")\n'
                'http_file = use_repo_rule("@bazel_tools//tools/build_defs/repo:http.bzl", "http_file")\n'
                'http_file(name = "locked_debian_payload", urls = [' + json.dumps(TOMLI_URL) + '], '
                'sha256 = ' + json.dumps(TOMLI_SHA256) + ', downloaded_file_path = "package.deb")\n')
            (consumer / "BUILD.bazel").write_text("")
            config = ROOT / "ci/source_mirrors.cfg"
            server = None
            requests = []
            if corrupt:
                class WrongPayload(BaseHTTPRequestHandler):
                    def do_GET(self):
                        requests.append(self.path)
                        payload = b"corrupt existing Debian payload\n"
                        self.send_response(200)
                        self.send_header("Content-Length", str(len(payload)))
                        self.end_headers()
                        self.wfile.write(payload)

                    def log_message(self, *_args):
                        pass

                server = ThreadingHTTPServer(("127.0.0.1", 0), WrongPayload)
                threading.Thread(target=server.serve_forever, daemon=True).start()
                config = work / "corrupt.cfg"
                # Keep the production match expressions. Make both mirror and
                # fallback serve invalid bytes so a healthy snapshot cannot hide
                # a checksum-validation regression.
                lines = []
                for line in (ROOT / "ci/source_mirrors.cfg").read_text().splitlines():
                    if line.startswith("rewrite (snapshot"):
                        line = line.rsplit(" ", 1)[0] + f" http://127.0.0.1:{server.server_port}/package.deb"
                    lines.append(line)
                config.write_text("\n".join(lines) + "\n")
            command = [os.environ["REGISTRY_CI_TEST_BAZEL"], "--batch", "--ignore_all_rc_files",
                       "--output_user_root=" + str(work / "bazel"), "--output_base=" + str(work / "output"),
                       "fetch", "--repo=@locked_debian_payload", "--incompatible_autoload_externally=",
                       "--repository_cache=" + str(cache), "--lockfile_mode=update",
                       "--experimental_downloader_config=" + str(config)]
            try:
                (artifacts / "command.json").write_text(json.dumps(command, indent=2) + "\n")
                with (artifacts / "fetch.log").open("w") as log:
                    result = subprocess.run(command, cwd=consumer, stdout=log,
                                            stderr=subprocess.STDOUT, timeout=180)
                transcript = (artifacts / "fetch.log").read_text()
                payload = cache / "content_addressable/sha256" / TOMLI_SHA256 / "file"
                if corrupt:
                    self.assertNotEqual(result.returncode, 0, transcript)
                    self.assertIn("Checksum", transcript)
                    self.assertTrue(requests)
                    self.assertEqual(set(requests), {"/package.deb"})
                    self.assertFalse(payload.exists(), "Corrupt payload entered the verified cache")
                else:
                    self.assertEqual(result.returncode, 0, transcript)
                    self.assertEqual(hashlib.sha256(payload.read_bytes()).hexdigest(), TOMLI_SHA256)
                (artifacts / "result.json").write_text(json.dumps({
                    "url": TOMLI_URL, "expected_sha256": TOMLI_SHA256,
                    "corrupt_mirror": corrupt, "status": "passed", "empty_repository_cache": True,
                    "compilation_or_package_actions_executed": False,
                    "production_config_sha256": hashlib.sha256((ROOT / "ci/source_mirrors.cfg").read_bytes()).hexdigest(),
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
