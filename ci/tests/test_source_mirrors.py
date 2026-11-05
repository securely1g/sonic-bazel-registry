"""Fetch unchanged BCR archives and exercise ordered mirror fallback with Bazel."""
from __future__ import annotations

import base64
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
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
from urllib.parse import quote
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[2]
CI_SPEC = importlib.util.spec_from_file_location("registry_ci_source_mirrors", ROOT / "ci/registry_ci.py")
assert CI_SPEC is not None and CI_SPEC.loader is not None
REGISTRY_CI = importlib.util.module_from_spec(CI_SPEC)
CI_SPEC.loader.exec_module(REGISTRY_CI)
PIGZ_SHA256 = "eb872b4f0e1f0ebe59c9f7bd8c506c4204893ba6a8492de31df416f0d5170fd0"
PIGZ_MODULE = "https://bcr.bazel.build/modules/pigz/2.8.bcr.2/MODULE.bazel"
ARM_ARCHIVES = (
    ("ape", "1.0.1", "sha512-YHlfxYHiCxzrifn5ywADS59XhmTk5u0rW/1fPepfk1C6/bXn3uwSADixLkvee6rAP9u2sulmHX0igt5F5+eqTA=="),
    ("download_utils", "1.0.1", "sha512-nsUJrJJjUWKzTQA187uWHhnBSqPA7t8Q6Rqry83Sj63Kf09L6xEFCR7thlnRUtbRbzabIKGr7JreouFdjjdarw=="),
    ("rules_coreutils", "1.0.1", "sha512-ViXfJnpIYJ/rhVAcq/WIc/SwekMKubAFS/1cVrziq9NoHkLBtXbf977l/fEknU1ElXtteVDtxOfgi8vcM+34Qg=="),
    ("rules_gzip", "1.0.0", "sha512-KK1A/NSvOaixXftdIRSBHt+QSPEk1ZorO2HtKY6o5KRP/i8KQ1hsDQPVwbCCi0++6pE529idMytTL/3SmhNmCQ=="),
    ("toolchain_utils", "1.0.2", "sha512-AXqtA9CzczVUdS5dw0dX332eaXZQhFcEZmf1iKALwsoKoT9Mboah7/j1JN9hZpzq6B5X7gpe83TPpya6yJZ6Lw=="),
)
ARM_RELEASE = "https://github.com/securely1g/sonic-bazel-registry/releases/download/ci-source-mirrors-20261104"
GAWK_SHA256 = "f8c3486509de705192138b00ef2c00bbbdd0e84c30d5c07d23fc73a9dc4cc9cc"
GAWK_MIRROR = "https://distfiles.macports.org/gawk/gawk-5.3.2.tar.xz"
GAWK_HOSTS = ("mirrors.kernel.org", "ftp.gnu.org", "ftpmirror.gnu.org")
LIBSFRAME_SNAPSHOT = "https://snapshot.debian.org/archive/debian/20260727T143429Z/pool/main/b/binutils/libsframe1_2.44-3_amd64.deb"
LIBAUDIT_SNAPSHOT = "https://snapshot.debian.org/archive/debian/20260727T143429Z/pool/main/a/audit/libaudit-dev_4.0.2-2+b2_amd64.deb"
LIBAUDIT_CONTENT_URL = "https://snapshot.debian.org/file/930f8fe502ed2d1b79243a03d1e1318c1bf30524"
# The libyang-python@3.1.0.sonic.6 generated APT lock pins these exact package bytes.
LIBSFRAME_SHA256 = "38f625dfdc582717029ac3a3e97c51d994ec2e7a0e9b230c6b44e40d1276311f"
DEBIAN_RELEASE_PACKAGES = (
    ("libcap2_2.75-10+deb13u1+b1_arm64.deb",
     "https://snapshot.debian.org/archive/debian/20260727T143429Z/pool/main/libc/libcap2/libcap2_2.75-10+deb13u1+b1_arm64.deb"),
    ("bash_5.2.37-2+b9_arm64.deb",
     "https://snapshot.debian.org/archive/debian/20260727T143429Z/pool/main/b/bash/bash_5.2.37-2+b9_arm64.deb"),
)
# Generated APT locks from native ARM validation and the cross-build survey
# preserve these exact bytes, including declared build-tool dependencies.
# Each tuple is (original URL, content locator, locked SHA256, size, optional CDN).
DEBIAN_CONTENT_PACKAGES = (
    ("https://snapshot.debian.org/archive/debian/20260727T143429Z/pool/main/g/glibc/libc-bin_2.41-12+deb13u3_arm64.deb",
     "2f97c88e63e698b86775350598dea8efb421df45",
     "02f366115bea79b87fe26c7dec4dc444f9fdcc76440905d88cc26dbef075511b", 551364, None),
    ("https://snapshot.debian.org/archive/debian/20260727T143429Z/pool/main/u/util-linux/uuid-dev_2.41-5_amd64.deb",
     "05b9652f442e9b33da16bb41cc69283e2a9b7c33",
     "fbc76c5c549192f52e7a03949108cdf28b1dc0751261495b7ef17cb8bf39dd8d", 48836, None),
    ("https://snapshot.debian.org/archive/debian-security/20260726T121236Z/pool/updates/main/c/c-ares/libc-ares-dev_1.34.5-1+deb13u1_arm64.deb",
     "109d7800bf370139268bea60e2ea7e2699cc3d48",
     "40d2336fb01e4b707ad8a6bfbad522fc7ddff3b057d16ee981237fb7cef5d95c", 224912,
     "https://deb.debian.org/debian-security/pool/updates/main/c/c-ares/libc-ares-dev_1.34.5-1+deb13u1_arm64.deb"),
    ("https://snapshot.debian.org/archive/debian-security/20260726T121236Z/pool/updates/main/o/openssl/openssl-provider-legacy_3.5.6-1~deb13u2_arm64.deb",
     "d5a41e70f8551fb076606ed0b1c0dab7fa9bc32d",
     "b099729f6a38d7d57f7f442f0f836c862673b9bb0ee65d757da6e3cdebbfd2a4", 310184, None),
    ("https://snapshot.debian.org/archive/debian-security/20260726T121236Z/pool/updates/main/o/openssl/openssl_3.5.6-1~deb13u2_arm64.deb",
     "4b411e66ee3d3106570389d5d1e022b15c1975a8",
     "1ee735e2480519bd1fd5f6576a879243bc81b9773059e1fa1ec8b8943c84e77c", 1466984, None),
)
SURVEY_CONTENT_PACKAGES = (
    ("https://snapshot.debian.org/archive/debian/20260727T143429Z/pool/main/u/util-linux/libuuid1_2.41-5_amd64.deb",
     "69561687e45ee4833a59400e51976ff05cf71c0d",
     "10247744737c1bb574f9667b3f06a3b43a5055c67bdfcc1945803451cc036db3", 37612, None),
    ("https://snapshot.debian.org/archive/debian/20260727T143429Z/pool/main/x/xapian-core/libxapian30_1.4.29-3_arm64.deb",
     "b3cef6d6dfd6511f04a77442026f81811313012e",
     "1652525c1c605b2169b3b27beecd01cbaa0e5abd7ec4d2029cbae2084dbde012", 1055832, None),
    ("https://snapshot.debian.org/archive/debian-security/20260726T121236Z/pool/updates/main/o/openssl/libssl-dev_3.5.6-1~deb13u2_armhf.deb",
     "a6e3b3b45aaf7799d6ab6ad71e09218a813866c8",
     "fc167d04049dfcf91ccff8687222a186be681cac2298ae89cf8523518ad04c88", 2570728, None),
    ("https://snapshot.debian.org/archive/debian-security/20260726T121236Z/pool/updates/main/k/krb5/libgssrpc4t64_1.21.3-5+deb13u1_amd64.deb",
     "3e0610e3b6f6d57539344d7a1f95da1ed442fd48",
     "ff88e52a6b6599851f3d44f7223f15123d9e5a0b02ed9a308c05c31fa88f7d73", 60132, None),
    ("https://snapshot.debian.org/archive/debian/20260727T143429Z/pool/main/u/util-linux/libblkid1_2.41-5_amd64.deb",
     "8413cb58799327072dd69a418e41fc05009cfd03",
     "bed93f11942524e5338074c46cce376197740635bf0745ccb7d259e0f6ce7117", 171276, None),
    ("https://snapshot.debian.org/archive/debian/20260727T143429Z/pool/main/g/glibc/libc6_2.41-12+deb13u3_arm64.deb",
     "8dd0cfbe0f5bd2c3923c8252c00c868bc6ac945e",
     "ff529924782d3286181188fc265a6a92e7fe28975fb3a925dc0e05c0ca66e52f", 2489480, None),
    ("https://snapshot.debian.org/archive/debian/20260727T143429Z/pool/main/p/python3.13/libpython3.13-dev_3.13.5-2+deb13u4_arm64.deb",
     "f0907e7116933f0437ac671e9946e4740fcef10b",
     "fd62da71db387aba934e4bd17cceaf0db1454ae9e1eae378c4d8329fbe856883", 4924800, None),
    ("https://snapshot.debian.org/archive/debian-security/20260726T121236Z/pool/updates/main/t/tiff/libtiff6_4.7.0-3+deb13u3_amd64.deb",
     "faa5bddd33fff3675e7b76863c6ef140347fb3b2",
     "6bb2038f36817ae1ee6d33df03917b21835dcc2e0f3e3e80a71390e83c171173", 345492, None),
)
DEBIAN_CONTENT_PACKAGES += SURVEY_CONTENT_PACKAGES
# BusyBox package inputs pinned by BCR rules_coreutils@1.0.1's MODULE.bazel.
BUSYBOX_PACKAGES = (
    ("amd64", "d161cd711fcf0d21a53dd7b9665933463de9fa6a37718e78ffee4d7732e1e02a", 937460),
    ("arm64", "76e03728f35dcc63b40ad52e5273c888ffd8eed254c0c9f871d5b4e31a485150", 830700),
)
BUSYBOX_SNAPSHOT_PREFIX = "https://snapshot-cloudflare.debian.org/archive/debian/20240210T223313Z/pool/main/b/busybox/"


def arm_urls(name, version):
    return (f"{ARM_RELEASE}/{name}-v{version}.tar.gz",
            f"https://gitlab.arm.com/bazel/{name}/-/releases/v{version}/downloads/src.tar.gz")


def debian_release_url(filename):
    return f"{ARM_RELEASE}/{quote(filename, safe='')}"


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
    def candidates(self, url):
        rewrites = [line.split()[1:] for line in (ROOT / "ci/source_mirrors.cfg").read_text().splitlines()
                    if line.startswith("rewrite ")]
        result = []
        for pattern, replacement in rewrites:
            matched = re.fullmatch(pattern, url.removeprefix("https://"))
            if matched:
                result.append(re.sub(r"\$(\d+)", lambda ref: matched.group(int(ref[1])), replacement))
        return result

    def test_only_timestamped_debian_binary_pool_paths_are_rewritten(self):
        for upstream in (LIBSFRAME_SNAPSHOT,
                         "https://snapshot.debian.org/archive/debian/20250101T010203Z/pool/main/f/foo/foo_2%3a1.0~rc1+dfsg-3_arm64.deb"):
            pool_path = upstream.split("/pool/", 1)[1]
            self.assertEqual(self.candidates(upstream), ["https://deb.debian.org/debian/pool/" + pool_path, upstream])
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
            self.assertEqual(self.candidates(other), [], other)

    def test_socat_patch_archive_has_one_exact_content_exception(self):
        upstream = "https://snapshot.debian.org/archive/debian/20241222T205329Z/pool/main/s/socat/socat_1.8.0.2-1.debian.tar.xz"
        content = "https://snapshot.debian.org/file/0475522901bd85478b944520b23e01e3f3c7d339"
        self.assertEqual(self.candidates(upstream), [content, upstream])
        for other in (
            upstream.replace("20241222T205329Z", "20241223T205329Z"),
            upstream.replace("1.8.0.2-1.debian", "1.8.0.2-2.debian"),
            upstream.replace("1.8.0.2-1.debian.tar.xz", "1.8.0.2.orig.tar.bz2"),
            upstream.replace("snapshot.debian.org", "snapshot-cloudflare.debian.org"),
            upstream.replace("snapshot.debian.org", "another.example"),
            upstream.replace("/archive/debian/", "/archive/debian-security/"),
            upstream.replace("/pool/main/s/socat/", "/pool/main/s/../"),
            upstream.replace("pool/main/s/socat/socat_1.8.0.2-1.debian.tar.xz",
                             "dists/trixie/main/source/Sources.xz"),
            upstream + "?query", upstream + "#fragment", upstream + ".sha256",
        ):
            self.assertEqual(self.candidates(other), [], other)

    def test_libaudit_content_address_is_limited_to_the_exact_pinned_package(self):
        self.assertEqual(self.candidates(LIBAUDIT_SNAPSHOT), [
            LIBAUDIT_CONTENT_URL,
            "https://deb.debian.org/debian/pool/main/a/audit/libaudit-dev_4.0.2-2+b2_amd64.deb",
            LIBAUDIT_SNAPSHOT,
        ])
        for other in (
            LIBAUDIT_SNAPSHOT.replace("20260727T143429Z", "20260728T143429Z"),
            LIBAUDIT_SNAPSHOT.replace("4.0.2-2+b2", "4.0.2-2+b3"),
            LIBAUDIT_SNAPSHOT.replace("amd64", "arm64"),
            LIBAUDIT_SNAPSHOT.replace("snapshot.debian.org", "another.example"),
            LIBAUDIT_SNAPSHOT + "?query", LIBAUDIT_SNAPSHOT + ".sha256",
        ):
            self.assertNotIn(LIBAUDIT_CONTENT_URL, self.candidates(other), other)

    def test_debian_release_mirrors_are_limited_to_exact_locked_inputs(self):
        for filename, upstream in DEBIAN_RELEASE_PACKAGES:
            mirror = debian_release_url(filename)
            self.assertEqual(self.candidates(upstream), [
                mirror,
                "https://deb.debian.org/debian/pool/" + upstream.split("/pool/", 1)[1],
                upstream,
            ])
            for other in (
                upstream.replace("20260727T143429Z", "20260728T143429Z"),
                upstream.replace("+", "+changed", 1),
                upstream.replace("_arm64.deb", "_amd64.deb"),
                upstream.replace("snapshot.debian.org", "another.example"),
                upstream + "?query", upstream + ".sha256",
            ):
                self.assertNotIn(mirror, self.candidates(other), other)

    def test_content_candidates_are_limited_to_exact_locked_packages(self):
        for upstream, locator, _checksum, _size, security_cdn in DEBIAN_CONTENT_PACKAGES:
            content = "https://snapshot.debian.org/file/" + locator
            expected = [content]
            if "/archive/debian/" in upstream:
                expected.append("https://deb.debian.org/debian/pool/" + upstream.split("/pool/", 1)[1])
            if security_cdn:
                expected.append(security_cdn)
            expected.append(upstream)
            self.assertEqual(self.candidates(upstream), expected)
            for other in (
                upstream.replace("202607", "202608"),
                upstream.replace(".deb", "+changed.deb"),
                re.sub(r"_(amd64|arm64|armhf)\.deb$", "_riscv64.deb", upstream),
                upstream.replace("snapshot.debian.org", "another.example"),
                upstream.replace("/pool/", "/different/"),
                upstream + "?query", upstream + ".sha256",
            ):
                self.assertNotEqual(other, upstream)
                self.assertNotIn(content, self.candidates(other), other)
                if security_cdn:
                    self.assertNotIn(security_cdn, self.candidates(other), other)

    def test_cloudflare_package_candidates_keep_standard_and_original_snapshots(self):
        for architecture, _checksum, _size in BUSYBOX_PACKAGES:
            upstream = BUSYBOX_SNAPSHOT_PREFIX + f"busybox-static_1.36.1-6_{architecture}.deb"
            self.assertEqual(self.candidates(upstream), [
                "https://deb.debian.org/debian/pool/main/b/busybox/" + upstream.rsplit("/", 1)[1],
                upstream.replace("snapshot-cloudflare.debian.org", "snapshot.debian.org"), upstream,
            ])
            for other in (
                upstream.replace("/archive/debian/", "/archive/debian-security/"),
                upstream.replace("20240210T223313Z/", ""),
                upstream.replace("pool/main/b/busybox/" + upstream.rsplit("/", 1)[1],
                                 "dists/bookworm/main/binary-amd64/Packages.xz"),
                upstream.removesuffix(".deb") + ".tar.xz", upstream + "?query",
                upstream.replace("snapshot-cloudflare.debian.org", "other.debian.org"),
            ):
                self.assertEqual(self.candidates(other), [], other)


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
        repos = [repo] if isinstance(repo, str) else repo
        command = [os.environ["REGISTRY_CI_TEST_BAZEL"], "--batch", "--ignore_all_rc_files",
                   "--output_user_root=" + str(work / "bazel"), "--output_base=" + str(work / "output"),
                   "fetch", *("--repo=@" + name for name in repos), "--registry=https://bcr.bazel.build/",
                   "--repository_cache=" + str(cache), "--lockfile_mode=update",
                   *REGISTRY_CI.HTTP_DOWNLOAD_FLAGS,
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
    def test_survey_content_candidates_preserve_locked_bytes_without_other_fallbacks(self):
        # Exercise only each production content candidate: an available original
        # snapshot must not hide a broken alternative in this cold-download proof.
        rules = (ROOT / "ci/source_mirrors.cfg").read_text().splitlines()
        with tempfile.TemporaryDirectory(prefix="registry-survey-content-") as temporary:
            work = Path(temporary)
            module = ('module(name = "survey_content_consumer")\n'
                      'http_file = use_repo_rule("@bazel_tools//tools/build_defs/repo:http.bzl", "http_file")\n')
            selected_rules, repos = [], []
            for index, (upstream, locator, checksum, _size, _cdn) in enumerate(SURVEY_CONTENT_PACKAGES):
                matching = []
                for line in rules:
                    if not line.startswith("rewrite "):
                        continue
                    _directive, pattern, replacement = line.split(None, 2)
                    if (re.fullmatch(pattern, upstream.removeprefix("https://"))
                            and replacement == "https://snapshot.debian.org/file/" + locator):
                        matching.append(line)
                self.assertEqual(len(matching), 1, upstream)
                selected_rules.extend(matching)
                repo = f"survey_package_{index}"
                repos.append(repo)
                module += f'http_file(name = {repo!r}, urls = [{upstream!r}], sha256 = {checksum!r})\n'
            config = work / "content-only.cfg"
            config.write_text("\n".join(selected_rules) + "\n")
            result, transcript, cache = self.fetch(work, module, repos, config)
            self.assertEqual(result.returncode, 0, transcript)
            for _upstream, _locator, checksum, size, _cdn in SURVEY_CONTENT_PACKAGES:
                package = cache / "content_addressable/sha256" / checksum / "file"
                self.assertEqual(package.stat().st_size, size)
                self.assertEqual(hashlib.sha256(package.read_bytes()).hexdigest(), checksum)

    def test_content_package_candidates_preserve_all_locked_hashes_with_empty_cache(self):
        with tempfile.TemporaryDirectory(prefix="registry-debian-content-") as temporary:
            work = Path(temporary)
            module = ('module(name = "debian_content_consumer")\n'
                      'http_file = use_repo_rule("@bazel_tools//tools/build_defs/repo:http.bzl", "http_file")\n')
            repos = []
            for index, (upstream, _locator, checksum, _size, _cdn) in enumerate(DEBIAN_CONTENT_PACKAGES):
                repo = f"locked_package_{index}"
                repos.append(repo)
                module += f'http_file(name = {repo!r}, urls = [{upstream!r}], sha256 = {checksum!r})\n'
            result, transcript, cache = self.fetch(work, module, repos, ROOT / "ci/source_mirrors.cfg")
            self.assertEqual(result.returncode, 0, transcript)
            for upstream, _locator, checksum, size, _cdn in DEBIAN_CONTENT_PACKAGES:
                with self.subTest(package=upstream):
                    package = cache / "content_addressable/sha256" / checksum / "file"
                    self.assertEqual(package.stat().st_size, size)
                    self.assertEqual(hashlib.sha256(package.read_bytes()).hexdigest(), checksum)

    def test_exact_content_candidates_satisfy_original_snapshot_requests(self):
        for upstream, locator, _checksum, _size, _cdn in DEBIAN_CONTENT_PACKAGES:
            with self.subTest(package=upstream):
                self.exercise_snapshot_fallback(upstream, ["/content/" + locator])

    def test_exact_content_candidates_keep_all_original_fallbacks(self):
        for upstream, locator, _checksum, _size, security_cdn in DEBIAN_CONTENT_PACKAGES:
            with self.subTest(package=upstream):
                expected = ["/content/" + locator]
                if "/archive/debian/" in upstream:
                    expected.append("/cdn/pool/" + upstream.split("/pool/", 1)[1])
                    expected.append("/snapshot/" + upstream.split("/archive/debian/", 1)[1])
                else:
                    if security_cdn:
                        expected.append("/security-cdn/pool/" + upstream.split("/pool/", 1)[1])
                    expected.append("/snapshot-security/" + upstream.split("/archive/debian-security/", 1)[1])
                self.exercise_snapshot_fallback(upstream, expected)

    def test_corrupt_security_content_candidate_falls_back_with_original_integrity(self):
        upstream, locator, _checksum, _size, _cdn = DEBIAN_CONTENT_PACKAGES[2]
        self.exercise_snapshot_fallback(upstream, [
            "/content/" + locator,
            "/security-cdn/pool/" + upstream.split("/pool/", 1)[1],
            "/snapshot-security/" + upstream.split("/archive/debian-security/", 1)[1],
        ], corrupt_primary=True)

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

    def test_busybox_candidates_preserve_both_architecture_hashes_with_empty_caches(self):
        for architecture, checksum, size in BUSYBOX_PACKAGES:
            with self.subTest(architecture=architecture), \
                    tempfile.TemporaryDirectory(prefix="registry-busybox-pool-") as temporary:
                work = Path(temporary)
                upstream = BUSYBOX_SNAPSHOT_PREFIX + f"busybox-static_1.36.1-6_{architecture}.deb"
                result, transcript, cache = self.fetch(work,
                    'module(name = "busybox_pool_consumer")\n'
                    'http_file = use_repo_rule("@bazel_tools//tools/build_defs/repo:http.bzl", "http_file")\n'
                    f'http_file(name = "busybox_package", urls = [{upstream!r}], sha256 = {checksum!r})\n',
                    "busybox_package", ROOT / "ci/source_mirrors.cfg")
                self.assertEqual(result.returncode, 0, transcript)
                package = cache / "content_addressable/sha256" / checksum / "file"
                self.assertEqual(package.stat().st_size, size)
                self.assertEqual(hashlib.sha256(package.read_bytes()).hexdigest(), checksum)

    def test_release_mirrors_satisfy_original_snapshot_fetches(self):
        for filename, upstream in DEBIAN_RELEASE_PACKAGES:
            with self.subTest(package=filename):
                self.exercise_snapshot_fallback(upstream, ["/mirror/" + filename])

    def test_unavailable_release_mirrors_keep_original_fallbacks(self):
        for filename, upstream in DEBIAN_RELEASE_PACKAGES:
            with self.subTest(package=filename):
                self.exercise_snapshot_fallback(upstream, [
                    "/mirror/" + filename,
                    "/cdn/pool/" + upstream.split("/pool/", 1)[1],
                    "/snapshot/" + upstream.split("/archive/debian/", 1)[1],
                ])

    def test_content_addressed_file_satisfies_the_original_snapshot_fetch(self):
        self.exercise_snapshot_fallback(LIBAUDIT_SNAPSHOT, ["/content/libaudit"])

    def test_unavailable_content_address_keeps_cdn_and_snapshot_fallbacks(self):
        self.exercise_snapshot_fallback(LIBAUDIT_SNAPSHOT, [
            "/content/libaudit",
            "/cdn/pool/main/a/audit/libaudit-dev_4.0.2-2+b2_amd64.deb",
            "/snapshot/20260727T143429Z/pool/main/a/audit/libaudit-dev_4.0.2-2+b2_amd64.deb",
        ])

    def test_missing_pool_version_falls_back_to_exact_snapshot_path(self):
        self.exercise_snapshot_fallback(LIBSFRAME_SNAPSHOT, [
            "/cdn/pool/main/b/binutils/libsframe1_2.44-3_amd64.deb",
            "/snapshot/20260727T143429Z/pool/main/b/binutils/libsframe1_2.44-3_amd64.deb",
        ])

    def test_cloudflare_original_is_retained_when_both_alternatives_are_missing(self):
        self.exercise_snapshot_fallback(
            LIBSFRAME_SNAPSHOT.replace("snapshot.debian.org", "snapshot-cloudflare.debian.org"), [
                "/cdn/pool/main/b/binutils/libsframe1_2.44-3_amd64.deb",
                "/snapshot/20260727T143429Z/pool/main/b/binutils/libsframe1_2.44-3_amd64.deb",
                "/cloudflare/20260727T143429Z/pool/main/b/binutils/libsframe1_2.44-3_amd64.deb",
            ])

    def exercise_snapshot_fallback(self, upstream, expected_requests, *, corrupt_primary=False):
        payload = b"locked Debian package fixture\n"
        checksum = hashlib.sha256(payload).hexdigest()
        requests = []

        class PackageSource(BaseHTTPRequestHandler):
            def do_GET(self):
                requests.append(self.path)
                corrupt = corrupt_primary and self.path == expected_requests[0]
                if self.path != expected_requests[-1] and not corrupt:
                    self.send_error(404)
                    return
                body = b"corrupt package bytes\n" if corrupt else payload
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), PackageSource)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with tempfile.TemporaryDirectory(prefix="registry-debian-fallback-") as temporary:
                work = Path(temporary)
                config = work / "local.cfg"
                config_text = ((ROOT / "ci/source_mirrors.cfg").read_text()
                               .replace(LIBAUDIT_CONTENT_URL, f"http://127.0.0.1:{server.server_port}/content/libaudit")
                               .replace("https://deb.debian.org/debian/$2", f"http://127.0.0.1:{server.server_port}/cdn/$2")
                               .replace("https://snapshot.debian.org/archive/debian/$1/$2",
                                        f"http://127.0.0.1:{server.server_port}/snapshot/$1/$2")
                               .replace("https://snapshot-cloudflare.debian.org/archive/debian/$1/$2",
                                        f"http://127.0.0.1:{server.server_port}/cloudflare/$1/$2"))
                for filename, _upstream in DEBIAN_RELEASE_PACKAGES:
                    config_text = config_text.replace(debian_release_url(filename),
                                                      f"http://127.0.0.1:{server.server_port}/mirror/{filename}")
                for snapshot, locator, _checksum, _size, cdn in DEBIAN_CONTENT_PACKAGES:
                    config_text = config_text.replace("https://snapshot.debian.org/file/" + locator,
                                                      f"http://127.0.0.1:{server.server_port}/content/{locator}")
                    if "/archive/debian-security/" in snapshot:
                        suffix = snapshot.split("/archive/debian-security/", 1)[1]
                        config_text = config_text.replace(snapshot,
                            f"http://127.0.0.1:{server.server_port}/snapshot-security/{suffix}")
                    if cdn:
                        config_text = config_text.replace(cdn,
                            f"http://127.0.0.1:{server.server_port}/security-cdn/pool/" + cdn.split("/pool/", 1)[1])
                config.write_text(config_text)
                result, transcript, cache = self.fetch(work,
                    'module(name = "debian_fallback_consumer")\n'
                    'http_file = use_repo_rule("@bazel_tools//tools/build_defs/repo:http.bzl", "http_file")\n'
                    f'http_file(name = "package_fixture", urls = [{upstream!r}], sha256 = {checksum!r})\n',
                    "package_fixture", config)
                self.assertEqual(result.returncode, 0, transcript)
                self.assertEqual(list(dict.fromkeys(requests)), expected_requests)
                self.assertEqual((cache / "content_addressable/sha256" / checksum / "file").read_bytes(), payload)
                if corrupt_primary:
                    self.assertIn("Checksum", transcript)
        finally:
            server.shutdown()
            server.server_close()


class SourceMirrorWorkflowScopeTest(unittest.TestCase):
    def test_matrix_is_preserved_for_every_branch_and_repository(self):
        workflow = (ROOT / ".github/workflows/registry-ci.yml").read_text()
        script = workflow.split("          python3 - <<'PY'\n", 1)[1].split("          PY\n", 1)[0]
        script = "\n".join(line[10:] for line in script.splitlines())
        matrix = {"include": [{"module": "original", "architecture": architecture}
                              for architecture in ("amd64", "arm64")]}
        for branch, repository in (
            ("codex/pigz-source-mirror", "securely1g/sonic-bazel-registry"),
            ("codex/debian-container-runners", "securely1g/sonic-bazel-registry"),
            ("other", "securely1g/sonic-bazel-registry"),
            ("codex/pigz-source-mirror", "another/fork"),
        ):
            with self.subTest(branch=branch, repository=repository):
                with tempfile.TemporaryDirectory(prefix="mirror-workflow-") as temporary:
                    output = Path(temporary) / "output"
                    env = {"EVENT_NAME": "pull_request", "HEAD_REF": branch,
                           "HEAD_REPOSITORY": repository, "GITHUB_OUTPUT": str(output)}
                    with mock.patch.dict(os.environ, env), \
                            mock.patch.object(Path, "read_text", return_value=json.dumps(matrix)):
                        exec(compile(script, "registry-ci-workflow", "exec"), {})
                    lines = output.read_text().splitlines()
                    self.assertEqual(json.loads(lines[0].removeprefix("matrix=")), matrix)
                    self.assertIn("has_jobs=true", lines)
                    self.assertIn("has_amd64_jobs=true", lines)
                    self.assertIn("has_arm64_jobs=true", lines)


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
                       *REGISTRY_CI.HTTP_DOWNLOAD_FLAGS,
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
