"""Fetch unchanged BCR archives and exercise ordered mirror fallback with Bazel."""
from __future__ import annotations

import base64
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
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[2]
PIGZ_SHA256 = "eb872b4f0e1f0ebe59c9f7bd8c506c4204893ba6a8492de31df416f0d5170fd0"
PIGZ_MODULE = "https://bcr.bazel.build/modules/pigz/2.8.bcr.2/MODULE.bazel"
ARM_ARCHIVES = (
    ("ape", "1.0.1", "sha512-YHlfxYHiCxzrifn5ywADS59XhmTk5u0rW/1fPepfk1C6/bXn3uwSADixLkvee6rAP9u2sulmHX0igt5F5+eqTA=="),
    ("rules_gzip", "1.0.0", "sha512-KK1A/NSvOaixXftdIRSBHt+QSPEk1ZorO2HtKY6o5KRP/i8KQ1hsDQPVwbCCi0++6pE529idMytTL/3SmhNmCQ=="),
    ("toolchain_utils", "1.0.2", "sha512-AXqtA9CzczVUdS5dw0dX332eaXZQhFcEZmf1iKALwsoKoT9Mboah7/j1JN9hZpzq6B5X7gpe83TPpya6yJZ6Lw=="),
)
ARM_RELEASE = "https://github.com/securely1g/sonic-bazel-registry/releases/download/ci-source-mirrors-20261104"
GAWK_SHA256 = "f8c3486509de705192138b00ef2c00bbbdd0e84c30d5c07d23fc73a9dc4cc9cc"
GAWK_MIRROR = "https://distfiles.macports.org/gawk/gawk-5.3.2.tar.xz"
GAWK_HOSTS = ("mirrors.kernel.org", "ftp.gnu.org", "ftpmirror.gnu.org")
LIBSFRAME_SNAPSHOT = "https://snapshot.debian.org/archive/debian/20260727T143429Z/pool/main/b/binutils/libsframe1_2.44-3_amd64.deb"
# The libyang-python@3.1.0.sonic.6 generated APT lock pins these exact package bytes.
LIBSFRAME_SHA256 = "38f625dfdc582717029ac3a3e97c51d994ec2e7a0e9b230c6b44e40d1276311f"


def arm_urls(name, version):
    return (f"{ARM_RELEASE}/{name}-v{version}.tar.gz",
            f"https://gitlab.arm.com/bazel/{name}/-/releases/v{version}/downloads/src.tar.gz")


class ArmSourceMirrorScopeTest(unittest.TestCase):
    def test_only_exact_pinned_arm_urls_get_github_then_upstream_candidates(self):
        rewrites = [line.split()[1:] for line in (ROOT / "ci/source_mirrors.cfg").read_text().splitlines()
                    if line.startswith("rewrite ")]
        for name, version, _integrity in ARM_ARCHIVES:
            github, upstream = arm_urls(name, version)
            candidates = [replacement for pattern, replacement in rewrites
                          if re.fullmatch(pattern, upstream.removeprefix("https://"))]
            self.assertEqual(candidates, [github, upstream])
            for other in (upstream + "?query", upstream + ".other", upstream.replace(version, "9.9.9"),
                          upstream.replace("gitlab.arm.com", "another.example"),
                          upstream.replace("/downloads/", "/different/")):
                self.assertFalse(any(re.fullmatch(pattern, other.removeprefix("https://"))
                                     for pattern, _replacement in rewrites), other)

    def test_gawk_candidates_preserve_each_original_url_and_exact_version(self):
        rewrites = [line.split()[1:] for line in (ROOT / "ci/source_mirrors.cfg").read_text().splitlines()
                    if line.startswith("rewrite ")]
        for host in GAWK_HOSTS:
            upstream = f"https://{host}/gnu/gawk/gawk-5.3.2.tar.xz"
            candidates = [replacement for pattern, replacement in rewrites
                          if re.fullmatch(pattern, upstream.removeprefix("https://"))]
            self.assertEqual(candidates, [GAWK_MIRROR, upstream])
            for other in (upstream.replace("5.3.2", "5.3.3"), upstream + "?query", upstream + ".sig"):
                self.assertFalse(any(re.fullmatch(pattern, other.removeprefix("https://"))
                                     for pattern, _replacement in rewrites), other)


class DebianPoolMirrorScopeTest(unittest.TestCase):
    def test_only_timestamped_debian_binary_pool_paths_are_rewritten(self):
        rewrites = [line.split()[1:] for line in (ROOT / "ci/source_mirrors.cfg").read_text().splitlines()
                    if line.startswith("rewrite ")]

        def candidates(url):
            result = []
            for pattern, replacement in rewrites:
                matched = re.fullmatch(pattern, url.removeprefix("https://"))
                if matched:
                    result.append(re.sub(r"\$(\d+)", lambda ref: matched.group(int(ref[1])), replacement))
            return result

        for upstream in (LIBSFRAME_SNAPSHOT,
                         "https://snapshot.debian.org/archive/debian/20250101T010203Z/pool/main/f/foo/foo_2%3a1.0~rc1+dfsg-3_arm64.deb"):
            pool_path = upstream.split("/pool/", 1)[1]
            self.assertEqual(candidates(upstream), ["https://deb.debian.org/debian/pool/" + pool_path, upstream])
        for other in (
            LIBSFRAME_SNAPSHOT.replace("snapshot.debian.org", "snapshot.example.org"),
            LIBSFRAME_SNAPSHOT.replace("/archive/debian/", "/archive/debian-security/"),
            LIBSFRAME_SNAPSHOT.replace("20260727T143429Z/", ""),
            LIBSFRAME_SNAPSHOT.replace("20260727T143429Z", "latest"),
            LIBSFRAME_SNAPSHOT.replace("pool/main/b/binutils/libsframe1_2.44-3_amd64.deb",
                                      "dists/trixie/main/binary-amd64/Packages.xz"),
            LIBSFRAME_SNAPSHOT.removesuffix(".deb") + ".tar.xz",
            LIBSFRAME_SNAPSHOT.removesuffix(".deb") + ".dsc",
            LIBSFRAME_SNAPSHOT.replace("/main/", "/../"),
            LIBSFRAME_SNAPSHOT + "?query", LIBSFRAME_SNAPSHOT + ".sha256",
        ):
            self.assertEqual(candidates(other), [], other)


@unittest.skipUnless(os.environ.get("REGISTRY_CI_TEST_BAZEL"),
                     "set REGISTRY_CI_TEST_BAZEL to exercise real Bazel downloads")
class ArchiveFetchTestCase(unittest.TestCase):
    def fetch(self, work, module_text, repo, config):
        consumer = work / "consumer"
        consumer.mkdir()
        (consumer / "MODULE.bazel").write_text(module_text)
        (consumer / "BUILD.bazel").write_text("")
        cache = work / "repository-cache"
        cache.mkdir()
        self.assertEqual(list(cache.iterdir()), [])
        command = [os.environ["REGISTRY_CI_TEST_BAZEL"], "--batch", "--ignore_all_rc_files",
                   "--output_user_root=" + str(work / "bazel"), "--output_base=" + str(work / "output"),
                   "fetch", "--repo=@" + repo, "--registry=https://bcr.bazel.build/",
                   "--repository_cache=" + str(cache), "--lockfile_mode=update",
                   "--experimental_downloader_config=" + str(config)]
        artifacts = work / "artifacts"
        artifacts.mkdir()
        (artifacts / "command.json").write_text(json.dumps(command, indent=2) + "\n")
        try:
            with (artifacts / "fetch.log").open("w") as log:
                result = subprocess.run(command, cwd=consumer, stdout=log, stderr=subprocess.STDOUT, timeout=300)
        finally:
            destination = os.environ.get("REGISTRY_CI_TEST_ARTIFACTS")
            if destination:
                shutil.copytree(artifacts, Path(destination) / work.name)
        transcript = (artifacts / "fetch.log").read_text()
        return result, transcript, cache


class ArmSourceMirrorIntegrationTest(ArchiveFetchTestCase):
    def test_github_archives_match_original_bcr_recipes_with_empty_cache(self):
        for name, version, integrity in ARM_ARCHIVES:
            with self.subTest(module=name), tempfile.TemporaryDirectory(prefix="registry-arm-mirror-") as temporary:
                work = Path(temporary)
                github, upstream = arm_urls(name, version)
                metadata = f"https://bcr.bazel.build/modules/{name}/{version}"
                with urlopen(metadata + "/source.json", timeout=60) as response:
                    source = json.load(response)
                self.assertEqual(source["url"], upstream)
                self.assertEqual(source["integrity"], integrity)
                checksum = base64.b64decode(integrity.removeprefix("sha512-")).hex()
                with urlopen(github, timeout=60) as response:
                    self.assertEqual(hashlib.sha512(response.read()).hexdigest(), checksum)
                # Exercise the real release asset, never silently pass via upstream.
                config = work / "github-only.cfg"
                config.write_text((ROOT / "ci/source_mirrors.cfg").read_text() + "\nblock gitlab.arm.com\n")
                result, transcript, cache = self.fetch(
                    work, f'module(name = "arm_mirror_consumer")\nbazel_dep(name = "{name}", version = "{version}")\n',
                    name, config)
                self.assertEqual(result.returncode, 0, transcript)
                archive = cache / "content_addressable/sha512" / checksum / "file"
                self.assertEqual(hashlib.sha512(archive.read_bytes()).hexdigest(), checksum)
                fetched = list((work / "output/external").glob(name + "+*/MODULE.bazel"))
                self.assertEqual(len(fetched), 1, fetched)
                with urlopen(metadata + "/MODULE.bazel", timeout=60) as response:
                    self.assertEqual(fetched[0].read_bytes(), response.read())

    def test_rewrite_order_fallback_and_integrity_with_local_sources(self):
        original = b"original fixture bytes\n"
        integrity = "sha512-" + base64.b64encode(hashlib.sha512(original).digest()).decode()
        checksum = hashlib.sha512(original).hexdigest()
        github, upstream = arm_urls("ape", "1.0.1")
        for primary, fallback in (("valid", "valid"), ("missing", "valid"),
                                  ("corrupt", "valid"), ("corrupt", "corrupt")):
            with self.subTest(primary=primary, fallback=fallback), \
                    tempfile.TemporaryDirectory(prefix="registry-arm-fallback-") as temporary:
                work = Path(temporary)
                requests = []

                class ArchiveSource(BaseHTTPRequestHandler):
                    def do_GET(self):
                        requests.append(self.path)
                        behavior = primary if self.path == "/primary" else fallback
                        if behavior == "missing":
                            self.send_error(404)
                            return
                        payload = original if behavior == "valid" else b"changed fixture bytes\n"
                        self.send_response(200)
                        self.send_header("Content-Length", str(len(payload)))
                        self.end_headers()
                        self.wfile.write(payload)

                    def log_message(self, *_args):
                        pass

                server = ThreadingHTTPServer(("127.0.0.1", 0), ArchiveSource)
                threading.Thread(target=server.serve_forever, daemon=True).start()
                try:
                    config = work / "local.cfg"
                    config.write_text((ROOT / "ci/source_mirrors.cfg").read_text()
                                      .replace(github, f"http://127.0.0.1:{server.server_port}/primary")
                                      .replace(upstream, f"http://127.0.0.1:{server.server_port}/upstream"))
                    result, transcript, cache = self.fetch(work,
                        'module(name = "fallback_consumer")\n'
                        'http_file = use_repo_rule("@bazel_tools//tools/build_defs/repo:http.bzl", "http_file")\n'
                        f'http_file(name = "archive_fixture", urls = [{upstream!r}], integrity = {integrity!r})\n',
                        "archive_fixture", config)
                    # Repeated HTTP attempts are allowed, but candidate order is fixed.
                    self.assertEqual(list(dict.fromkeys(requests)),
                                     ["/primary"] if primary == "valid" else ["/primary", "/upstream"])
                    archive = cache / "content_addressable/sha512" / checksum / "file"
                    if fallback == "corrupt":
                        self.assertNotEqual(result.returncode, 0, transcript)
                        self.assertFalse(archive.exists(), "Corrupt bytes entered the verified cache")
                    else:
                        self.assertEqual(result.returncode, 0, transcript)
                        self.assertEqual(archive.read_bytes(), original)
                    if primary == "corrupt":
                        self.assertIn("Checksum", transcript)
                finally:
                    server.shutdown()
                    server.server_close()


class GawkSourceMirrorIntegrationTest(ArchiveFetchTestCase):
    def test_gawk_mirror_preserves_published_integrity_with_empty_cache(self):
        source = json.loads((ROOT / "modules/gawk/5.3.2.sonic.1/source.json").read_text())
        self.assertEqual(base64.b64decode(source["integrity"].removeprefix("sha256-")).hex(), GAWK_SHA256)
        urls = [source["url"], *source["mirror_urls"]]
        self.assertEqual(urls, [f"https://{host}/gnu/gawk/gawk-5.3.2.tar.xz" for host in GAWK_HOSTS])
        with tempfile.TemporaryDirectory(prefix="registry-gawk-mirror-") as temporary:
            work = Path(temporary)
            config = work / "macports-only.cfg"
            # The regression must fetch the mirror, not silently succeed upstream.
            config.write_text((ROOT / "ci/source_mirrors.cfg").read_text()
                              + "\n" + "\n".join("block " + host for host in GAWK_HOSTS) + "\n")
            result, transcript, cache = self.fetch(work,
                'module(name = "gawk_mirror_consumer")\n'
                'http_file = use_repo_rule("@bazel_tools//tools/build_defs/repo:http.bzl", "http_file")\n'
                f'http_file(name = "gawk_archive", urls = {urls!r}, integrity = {source["integrity"]!r})\n',
                "gawk_archive", config)
            self.assertEqual(result.returncode, 0, transcript)
            archive = cache / "content_addressable/sha256" / GAWK_SHA256 / "file"
            self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(), GAWK_SHA256)


class DebianPoolMirrorIntegrationTest(ArchiveFetchTestCase):
    def test_pool_candidates_preserve_locked_package_hash_with_empty_cache(self):
        with tempfile.TemporaryDirectory(prefix="registry-debian-pool-") as temporary:
            work = Path(temporary)
            # Old versions may leave the CDN pool; keep the production snapshot fallback.
            config = ROOT / "ci/source_mirrors.cfg"
            result, transcript, cache = self.fetch(work,
                'module(name = "debian_pool_consumer")\n'
                'http_file = use_repo_rule("@bazel_tools//tools/build_defs/repo:http.bzl", "http_file")\n'
                f'http_file(name = "libsframe_package", urls = [{LIBSFRAME_SNAPSHOT!r}], sha256 = {LIBSFRAME_SHA256!r})\n',
                "libsframe_package", config)
            self.assertEqual(result.returncode, 0, transcript)
            package = cache / "content_addressable/sha256" / LIBSFRAME_SHA256 / "file"
            self.assertEqual(package.stat().st_size, 78360)
            self.assertEqual(hashlib.sha256(package.read_bytes()).hexdigest(), LIBSFRAME_SHA256)

    def test_missing_pool_version_falls_back_to_exact_snapshot_path(self):
        payload = b"locked Debian package fixture\n"
        checksum = hashlib.sha256(payload).hexdigest()
        requests = []

        class PackageSource(BaseHTTPRequestHandler):
            def do_GET(self):
                requests.append(self.path)
                if self.path.startswith("/cdn/"):
                    self.send_error(404)
                    return
                self.send_response(200)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *_args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), PackageSource)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with tempfile.TemporaryDirectory(prefix="registry-debian-fallback-") as temporary:
                work = Path(temporary)
                config = work / "local.cfg"
                config.write_text((ROOT / "ci/source_mirrors.cfg").read_text()
                                  .replace("https://deb.debian.org/debian/$2", f"http://127.0.0.1:{server.server_port}/cdn/$2")
                                  .replace("https://snapshot.debian.org/archive/debian/$1/$2",
                                           f"http://127.0.0.1:{server.server_port}/snapshot/$1/$2"))
                result, transcript, cache = self.fetch(work,
                    'module(name = "debian_fallback_consumer")\n'
                    'http_file = use_repo_rule("@bazel_tools//tools/build_defs/repo:http.bzl", "http_file")\n'
                    f'http_file(name = "package_fixture", urls = [{LIBSFRAME_SNAPSHOT!r}], sha256 = {checksum!r})\n',
                    "package_fixture", config)
                self.assertEqual(result.returncode, 0, transcript)
                self.assertEqual(list(dict.fromkeys(requests)), [
                    "/cdn/pool/main/b/binutils/libsframe1_2.44-3_amd64.deb",
                    "/snapshot/20260727T143429Z/pool/main/b/binutils/libsframe1_2.44-3_amd64.deb",
                ])
                self.assertEqual((cache / "content_addressable/sha256" / checksum / "file").read_bytes(), payload)
        finally:
            server.shutdown()
            server.server_close()


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
