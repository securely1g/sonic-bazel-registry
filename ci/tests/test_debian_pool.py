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


def snapshot_fallbacks(url):
    """The maintained baseline keeps the exact original URL as fallback."""
    return [url]


class DebianPoolRoutingTest(unittest.TestCase):
    def test_macsec_libteam_libss2_uses_only_the_verified_amd64_content(self):
        # PR177 job127020338914 selected ss-dev's libss2 dependency after
        # opting in to the previous shared config; pool404/Snapshot503 failed.
        original = "https://snapshot.debian.org/archive/debian/20260727T143429Z/pool/main/e/e2fsprogs/libss2_1.47.2-3+b11_amd64.deb"
        self.assertEqual(routed_urls(original), [
            "https://snapshot.debian.org/file/458f436ed67e7f80aed736c6665c6b725301024c",
            "https://deb.debian.org/debian/pool/main/e/e2fsprogs/libss2_1.47.2-3+b11_amd64.deb",
            *snapshot_fallbacks(original),
        ])
        for changed in (
            original.replace("3+b11", "3+b12"),
            original.replace("_amd64", "_arm64"),
            original.replace("20260727T143429Z", "20260726T143429Z"),
            original.replace("libss2_", "libss2-dbg_"),
            original.replace("/pool/main/", "/pool/contrib/"),
        ):
            with self.subTest(url=changed):
                self.assertEqual(routed_urls(changed), [
                    "https://deb.debian.org/debian/pool/" + changed.split("/pool/", 1)[1],
                    *snapshot_fallbacks(changed),
                ])
        for unchanged in (
            original + "?alternate=1", original + "#fragment",
            original.replace("snapshot.debian.org", "other.example"),
        ):
            with self.subTest(url=unchanged):
                self.assertEqual(routed_urls(unchanged), snapshot_fallbacks(unchanged))

    def test_macsec_amd64_analysis_libc6_inputs_use_verified_content(self):
        # AMD64 jobs126958076493/126958077370/126958076632 fetch these
        # two locked package records while preparing the multiarch sysroot.
        for architecture, content_id in (
            ("amd64", "11449623c6859d9164dff8aedbcf023edaddc513"),
            ("arm64", "8dd0cfbe0f5bd2c3923c8252c00c868bc6ac945e"),
        ):
            relative = f"main/g/glibc/libc6_2.41-12+deb13u3_{architecture}.deb"
            original = "https://snapshot.debian.org/archive/debian/20260727T143429Z/pool/" + relative
            with self.subTest(architecture=architecture):
                self.assertEqual(routed_urls(original), [
                    "https://snapshot.debian.org/file/" + content_id,
                    "https://deb.debian.org/debian/pool/" + relative,
                    *snapshot_fallbacks(original),
                ])
                for changed in (
                    original.replace("deb13u3", "deb13u4"),
                    original.replace("_" + architecture, "_armhf"),
                    original.replace("20260727T143429Z", "20260726T143429Z"),
                    original.replace("libc6_", "libc6-dbg_"),
                    original.replace("/pool/main/", "/pool/contrib/"),
                ):
                    self.assertEqual(routed_urls(changed), [
                        "https://deb.debian.org/debian/pool/" + changed.split("/pool/", 1)[1],
                        *snapshot_fallbacks(changed),
                    ])
                for unchanged in (
                    original + "?alternate=1", original + "#fragment",
                    original.replace("snapshot.debian.org", "other.example"),
                ):
                    self.assertEqual(routed_urls(unchanged), snapshot_fallbacks(unchanged))

    def test_eventd_trixie_headers_use_only_the_verified_content_route(self):
        # FRR163 Eventd AMD64 job126967800467 failed its initial aquery on
        # this exact URL. The same 2,859,420 bytes are pinned by SHA256
        # c514b81492fc01c573ecfc809f9b460023d50e5006848c4caf78997bf1f776a5.
        original = "https://snapshot.debian.org/archive/debian-security/20260726T121236Z/pool/updates/main/l/linux/linux-libc-dev_6.12.96-1_all.deb"
        self.assertEqual(routed_urls(original), [
            "https://snapshot.debian.org/file/66b33fe93d5d572e06cdabdd49d01c7b4947cfc7",
            "https://deb.debian.org/debian-security/pool/updates/main/l/linux/linux-libc-dev_6.12.96-1_all.deb",
            *snapshot_fallbacks(original),
        ])
        for changed in (
            original.replace("6.12.96-1", "6.12.97-1"),
            original.replace("_all", "_amd64"),
            original.replace("_all", "_arm64"),
            original.replace("20260726T121236Z", "20260725T121236Z"),
            original.replace("linux-libc-dev", "linux-headers"),
            original.replace("/updates/main/", "/updates/contrib/"),
        ):
            with self.subTest(url=changed):
                self.assertEqual(routed_urls(changed), [changed])
        for unchanged in (original + "?alternate=1", original + "#fragment",
                          original.replace("snapshot.debian.org", "other.example")):
            with self.subTest(url=unchanged):
                self.assertEqual(routed_urls(unchanged), snapshot_fallbacks(unchanged))

    def test_actual_bookworm_failure_uses_verified_content_before_prior_routes(self):
        # Registry226 run41895100402 retained the actual failed lock. The
        # repository still requires SHA256 ea265b1dff21ab2e4b22b38097031f8d63fb940ecb89427659655598860efc0f;
        # this SHA1-derived URL changes delivery, not the checksum policy.
        original = "https://snapshot.debian.org/archive/debian-security/20260726T121236Z/pool/updates/main/l/linux/linux-libc-dev_6.1.177-1_amd64.deb"
        self.assertEqual(routed_urls(original), [
            "https://snapshot.debian.org/file/aed472fca7f9b98fdb7103b974db264cb60c2248",
            "https://deb.debian.org/debian-security/pool/updates/main/l/linux/linux-libc-dev_6.1.177-1_amd64.deb",
            *snapshot_fallbacks(original),
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
                self.assertEqual(routed_urls(changed), [changed])
        for unchanged in (original + "?alternate=1", original + "#fragment",
                          original.replace("snapshot.debian.org", "other.example")):
            with self.subTest(url=unchanged):
                self.assertEqual(routed_urls(unchanged), snapshot_fallbacks(unchanged))

    def test_selected_historical_payloads_use_content_before_dated_snapshot(self):
        # The original four routes match Source83 run41909259565's selected
        # SHA256-pinned payloads; libpython-minimal failed fresh
        # analysis after the initial 15 builds and 12 tests passed.
        # Libteam162 run41900723985 attempt2 also failed on the exact libheif URL.
        # FRR163 inherited-image jobs126822668186/126822668789 failed on
        # libaudit-dev/uuid-dev respectively; both selected AMD64 payloads.
        # Its YANG job126930441231 failed on the exact libc6-dev sysroot input.
        # Libteam162 AMD64 job126980465955 failed on libmount1 via Graphviz.
        # FRR163 OCI AMD64 job126967800025 failed on jq during Sysmgr analysis.
        # MACsec177 AMD64 job126958076273 failed on the declared gzip build tool.
        for relative, content_id in [
            ("main/g/gzip/gzip_1.13-1_amd64.deb",
             "17e2275e726dad554ab38aa3f3d240f5270923cb"),
            ("main/j/jq/jq_1.7.1-6+deb13u2_amd64.deb",
             "5556211154d1adb33a69780c9b9385f7cf79fda9"),
            ("main/u/util-linux/libmount1_2.41-5_amd64.deb",
             "a82622f9dbedc5d438d8791f4e3a59f6f9976d88"),
            ("main/libh/libheif/libheif1_1.19.8-1_amd64.deb",
             "04d63b7e722e47ed3e0cd74aa01066c6d382621d"),
            # PR177 shared SWSS AMD64 job127057690672 failed via Graphviz.
            ("main/libh/libheif/libheif-plugin-dav1d_1.19.8-1_amd64.deb",
             "4db82883543536a32eb80350a3ac4149d85009de"),
            ("main/a/audit/libaudit-dev_4.0.2-2+b2_amd64.deb",
             "930f8fe502ed2d1b79243a03d1e1318c1bf30524"),
            ("main/u/util-linux/uuid-dev_2.41-5_amd64.deb",
             "05b9652f442e9b33da16bb41cc69283e2a9b7c33"),
            ("main/g/glibc/libc6-dev_2.41-12+deb13u3_amd64.deb",
             "fbb9e46e11e1a8365a4f067eb9d6ec10251df100"),
            ('main/c/cdebconf/libdebconfclient0_0.280_amd64.deb',
             '219dec5cd95ea5be91161ab1d30dc3f19efb6e01'),
            ('main/p/python3.13/libpython3.13_3.13.5-2+deb13u4_amd64.deb',
             'a817f92905b030fcbca7d433db7dc4dcccf91c3d'),
            ('main/p/python3.13/libpython3.13-minimal_3.13.5-2+deb13u4_amd64.deb',
             'd63097e4bb174c04bfc29e38e6270b43c2db9c0b'),
            # FRR163 jobs127327932746/127327935067/127327933410
            # failed analysis on these unchanged Python/Perl inputs.
            ('main/p/python3.13/libpython3.13-stdlib_3.13.5-2+deb13u4_amd64.deb',
             '34446b6d753038d30cc9dfb5bf17987ff56071da'),
            ('main/p/perl/perl_5.40.1-6_amd64.deb',
             '9c5005df956b8fa8a3f487c175499e6029669465'),
            ('main/libs/libselinux/libselinux1_3.8.1-1_amd64.deb',
             '44b247687c034c8a4142204f0827f7286614b354'),
        ]:
            original = "https://snapshot.debian.org/archive/debian/20260727T143429Z/pool/" + relative
            with self.subTest(url=original):
                self.assertEqual(routed_urls(original), [
                    "https://snapshot.debian.org/file/" + content_id,
                    "https://deb.debian.org/debian/pool/" + relative,
                    *snapshot_fallbacks(original),
                ])
                other_arch = original.replace("_amd64", "_arm64")
                # These ARM64 siblings have independently verified locked bytes.
                other_content = {
                    "main/u/util-linux/uuid-dev_2.41-5_amd64.deb":
                        ["https://snapshot.debian.org/file/cb5244c39df10c7ce2573dbf21944fe03d8a436b"],
                    "main/u/util-linux/libmount1_2.41-5_amd64.deb":
                        ["https://snapshot.debian.org/file/81aee071e0a7fff9504c0ec2cbf6acf665ebf0bb"],
                }.get(relative, [])
                self.assertEqual(routed_urls(other_arch), [
                    *other_content,
                    "https://deb.debian.org/debian/pool/" + other_arch.split("/pool/", 1)[1],
                    *snapshot_fallbacks(other_arch),
                ])
                for changed in (
                    original.replace("_amd64", "_armhf"),
                    original.replace("20260727T143429Z", "20260726T143429Z"),
                    original.replace("_amd64.deb", "+different_amd64.deb"),
                    original.replace("/pool/main/", "/pool/contrib/"),
                ):
                    self.assertEqual(routed_urls(changed), [
                        "https://deb.debian.org/debian/pool/" + changed.split("/pool/", 1)[1],
                        *snapshot_fallbacks(changed),
                    ])
                for unchanged in (original + "?alternate=1", original + "#fragment",
                                  original.replace("snapshot.debian.org", "other.example")):
                    self.assertEqual(routed_urls(unchanged), snapshot_fallbacks(unchanged))

    def test_actual_failed_payloads_keep_original_snapshot_second(self):
        for original in [TOMLI_URL,
            "https://snapshot.debian.org/archive/debian/20260727T143429Z/pool/main/t/thrift/libthrift-dev_0.19.0-4+b1_armhf.deb",
            "https://snapshot.debian.org/archive/debian/20260727T143429Z/pool/main/g/gmp/libgmp-dev_6.3.0+dfsg-3_armhf.deb",
            "https://snapshot.debian.org/archive/debian/20260727T143429Z/pool/main/g/glibc/libc6-dbg_2.41-12+deb13u3_amd64.deb",
            "https://snapshot.debian.org/archive/debian-security/20260726T121236Z/pool/updates/main/o/openssl/libssl-dev_3.5.6-1~deb13u2_armhf.deb"]:
            with self.subTest(url=original):
                archive, relative = original.split("/archive/", 1)[1].split("/", 1)
                pool = relative.split("/pool/", 1)[1]
                expected = [original] if archive == "debian-security" else [
                    f"https://deb.debian.org/{archive}/pool/{pool}", original]
                if original == "https://snapshot.debian.org/archive/debian-security/20260726T121236Z/pool/updates/main/o/openssl/libssl-dev_3.5.6-1~deb13u2_armhf.deb":
                    expected.insert(0, "https://snapshot.debian.org/file/a6e3b3b45aaf7799d6ab6ad71e09218a813866c8")
                self.assertEqual(routed_urls(original), expected)

    def test_indexes_sources_and_other_hosts_keep_maintained_routes(self):
        for url in [
            "https://snapshot.debian.org/archive/debian/20260727T143429Z/dists/trixie/Release",
            "https://snapshot.debian.org/archive/debian-security/20260726T121236Z/dists/trixie-security/main/binary-amd64/Packages.xz",
            TOMLI_URL.replace(".deb", ".dsc"), TOMLI_URL.replace(".deb", ".orig.tar.gz"),
            TOMLI_URL.replace("snapshot.debian.org", "other.example"),
            TOMLI_URL + "?alternate=1", TOMLI_URL + "#fragment",
            TOMLI_URL.replace("20260727T143429Z", "latest"),
        ]:
            with self.subTest(url=url):
                self.assertEqual(routed_urls(url), snapshot_fallbacks(url))

    def test_existing_pigz_mirror_is_preserved(self):
        self.assertEqual(routed_urls("https://zlib.net/pigz/pigz-2.8.tar.gz"),
                         ["https://distfiles.macports.org/pigz/pigz-2.8.tar.gz"])
        original = "https://zlib.net/pigz/pigz-2.9.tar.gz"
        self.assertEqual(routed_urls(original), [original])

    def test_exact_workflow_scope_and_rejected_changes(self):
        workflow = (ROOT / ".github/workflows/registry-ci.yml").read_text()
        script = workflow.split("          python3 - <<'PY'\n", 1)[1].split("          PY\n", 1)[0]
        script = "\n".join(line[10:] for line in script.splitlines())
        original = {"include": [{"module": "original", "architecture": "amd64"}]}
        cases = [
            ("pull_request", BRANCH, "securely1g/sonic-bazel-registry", "ci/source_mirrors.cfg", []),
            ("pull_request", BRANCH, "securely1g/sonic-bazel-registry", "ci/tests/test_source_mirrors.py", []),
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
                    outputs = dict(line.split("=", 1) for line in output.read_text().splitlines())
                    self.assertEqual(json.loads(outputs["amd64_matrix"])["include"], expected)
                    self.assertEqual(json.loads(outputs["arm64_matrix"])["include"], [])
                    self.assertEqual(outputs["has_amd64_jobs"], str(bool(expected)).lower())
                    self.assertEqual(outputs["has_arm64_jobs"], "false")


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
                # fallbacks serve invalid bytes so a healthy snapshot cannot hide
                # a checksum-validation regression.
                lines = []
                for line in (ROOT / "ci/source_mirrors.cfg").read_text().splitlines():
                    if line.startswith("rewrite ") and "snapshot" in line.split()[1]:
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
