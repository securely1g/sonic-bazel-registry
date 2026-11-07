"""Private download preference, integrity, and wrapper failure-path evidence."""
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import threading
import unittest
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("private_mirrors", ROOT / "ci/private_mirrors.py")
MIRRORS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MIRRORS)
MANIFEST = MIRRORS.load_manifest()
ENVIRONMENT = {
    key: f"https://private-mirror.example.test/archive/{archive}/"
    for key, archive in MIRRORS.MIRROR_ROOTS
}


def current_snapshots():
    return [(key, archive, MANIFEST[archive]["current"])
            for key, archive in MIRRORS.MIRROR_ROOTS]


def candidates(config, url):
    values = []
    scheme, without_scheme = url.split("://", 1)
    for line in config.splitlines():
        if not line.startswith("rewrite "):
            continue
        _, pattern, replacement = line.split()
        match = re.fullmatch(pattern, without_scheme)
        if match:
            value = re.sub(r"\$(\d+)", lambda m: match.group(int(m[1])), replacement)
            values.append(value if value.startswith(("http://", "https://")) else f"{scheme}://{value}")
    return list(dict.fromkeys(values))


class PrivateMirrorConfigTest(unittest.TestCase):
    def test_preference_preserves_existing_public_routes_and_originals(self):
        public = (ROOT / "ci/source_mirrors.cfg").read_text()
        combined = MIRRORS.configuration(public, ENVIRONMENT)
        for key, archive, snapshot, suffix, _sha in MIRRORS.probe_packages():
            for host in ("snapshot.debian.org", "snapshot-cloudflare.debian.org"):
                original = f"https://{host}/archive/{archive}/{snapshot}/{suffix}"
                expected = [ENVIRONMENT[key] + snapshot + "/" + suffix,
                            *candidates(public, original), original]
                self.assertEqual(candidates(combined, original), list(dict.fromkeys(expected)))

    def test_dated_indexes_and_pool_paths_preserve_snapshot_identity(self):
        for key, archive, snapshot in current_snapshots():
            config = MIRRORS.configuration("", ENVIRONMENT)
            for suffix in ("dists/trixie/InRelease",
                           "dists/trixie/main/binary-amd64/by-hash/SHA256/" + "a" * 64,
                           "pool/main/x/example/example_1%3a2+3~rc1_amd64.deb"):
                original = f"https://snapshot.debian.org/archive/{archive}/{snapshot}/{suffix}"
                self.assertEqual(candidates(config, original),
                                 [ENVIRONMENT[key] + snapshot + "/" + suffix, original])
                for changed in (original.replace(snapshot, "latest"), original + "?q=1",
                                original.replace("snapshot.debian.org", "another.example"),
                                original.replace(suffix, "pool/../secret"),
                                original.replace(suffix, "pool/%2e%2e/secret"),
                                original.replace(suffix, "pool/main%2f..%2fsecret")):
                    self.assertEqual(candidates(config, changed), [])

    def test_known_cdn_binary_and_source_files_try_the_matching_snapshot(self):
        public = (ROOT / "ci/source_mirrors.cfg").read_text()
        config = MIRRORS.configuration(public, ENVIRONMENT)
        routes = (
            ("DEBIAN_MIRROR_ROOT", "deb.debian.org/debian", "pool/main"),
            ("DEBIAN_SECURITY_MIRROR_ROOT", "deb.debian.org/debian-security", "pool/updates/main"),
            ("DEBIAN_SECURITY_MIRROR_ROOT", "security.debian.org/debian-security", "pool/updates/main"),
        )
        for key, origin, pool in routes:
            for scheme in ("https", "http"):
                for package in ("example_1%3a2+3~rc1_amd64.deb", "example_2%2B3_arm64.udeb",
                                "example_2.orig.tar.bz2", "example_2-1.debian.tar.xz", "example_2-1.dsc"):
                    suffix = f"{pool}/e/example/{package}"
                    original = f"{scheme}://{origin}/{suffix}"
                    with self.subTest(original=original):
                        archive = origin.split("/", 1)[1]
                        base = ENVIRONMENT[key] + MANIFEST[archive]["current"] + "/"
                        if not package.endswith((".deb", ".udeb")):
                            base = base.split("archive/", 1)[0] + archive + "/"
                        self.assertEqual(candidates(config, original), [base + suffix, original])
                        self.assertEqual(candidates(MIRRORS.configuration(public, {}), original), [])
                        other = {k: v for k, v in ENVIRONMENT.items() if k != key}
                        self.assertEqual(candidates(MIRRORS.configuration(public, other), original), [])

    def test_cdn_rules_exclude_indexes_unknown_files_hosts_and_path_escapes(self):
        config = MIRRORS.configuration("", ENVIRONMENT)
        original = "https://deb.debian.org/debian/pool/main/e/example/example_1_amd64.deb"
        excluded = (
            original + "?download=1", original + "#fragment",
            original.replace("deb.debian.org", "archive.debian.org"),
            original.replace("deb.debian.org", "ftp.debian.org"),
            original.replace("deb.debian.org", "deb.debian.org.example.test"),
            original.removesuffix(".deb") + ".sh",
            original.replace("pool/main", "pool/updates/main"),
            original.replace("/e/example/", "/e/../"),
            original.replace("/e/example/", "/e/%2e%2e/"),
            original.replace("example_1_amd64", "example%2f..%2fprivate"),
            "https://deb.debian.org/debian/dists/trixie/InRelease",
            "https://security.debian.org/debian-security/dists/trixie-security/InRelease",
            original.replace("deb.debian.org/debian", "security.debian.org/debian-security"),
        )
        for url in excluded:
            with self.subTest(url=url):
                self.assertEqual(candidates(config, url), [])

    def test_historical_snapshot_inputs_keep_their_dates_and_public_fallbacks(self):
        public = (ROOT / "ci/source_mirrors.cfg").read_text()
        config = MIRRORS.configuration(public, ENVIRONMENT)
        archive = ENVIRONMENT["DEBIAN_MIRROR_ROOT"]
        for host, path in (
            ("snapshot.debian.org", "20241222T205329Z/pool/main/s/socat/socat_1.8.0.2.orig.tar.bz2"),
            ("snapshot-cloudflare.debian.org", "20240210T223313Z/pool/main/b/busybox/busybox-static_1.36.1-6_amd64.deb"),
        ):
            original = f"https://{host}/archive/debian/{path}"
            expected = [archive + path, *candidates(public, original), original]
            self.assertEqual(candidates(config, original), list(dict.fromkeys(expected)))

    def test_public_index_fallback_only_for_published_probe_formats(self):
        public = (ROOT / "ci/source_mirrors.cfg").read_text()
        for key, archive, date in current_snapshots():
            cfg = MIRRORS.configuration(public, ENVIRONMENT)
            for suite, formats in MANIFEST[archive]["snapshots"][date].items():
                for arch in ("amd64", "arm64", "armhf"):
                    for index in (f"binary-{arch}/Packages", f"Contents-{arch}"):
                        for ext in ("", ".xz", ".gz", ".bz2"):
                            path = f"dists/{suite}/main/{index}{ext}"
                            origin = f"https://snapshot.debian.org/archive/{archive}/{date}/{path}"
                            routes = candidates(cfg, origin)
                            self.assertEqual(routes[0], ENVIRONMENT[key] + date + "/" + path)
                            listed = ext in formats["Contents" if index.startswith("Contents") else "Packages"]
                            self.assertEqual(origin in routes, listed, origin)

    def test_gnu_m4_alias_prefers_the_identical_private_debian_source(self):
        public = (ROOT / "ci/source_mirrors.cfg").read_text()
        combined = MIRRORS.configuration(public, ENVIRONMENT)
        path = "/debian/pool/main/m/m4/m4_1.4.18.orig.tar.xz"
        for prefix in ("mirrors.kernel.org/gnu", "ftp.gnu.org/gnu", "ftpmirror.gnu.org"):
            origin = f"https://{prefix}/m4/m4-1.4.18.tar.xz"
            self.assertEqual(candidates(public, origin), ["https://deb.debian.org" + path, origin])
            self.assertEqual(candidates(combined, origin),
                             ["https://private-mirror.example.test" + path, *candidates(public, origin)])
            self.assertEqual(candidates(combined, origin.replace("1.4.18", "1.4.19")), [])

    def test_net_snmp_alias_preserves_exact_source_and_ordered_fallbacks(self):
        public = (ROOT / "ci/source_mirrors.cfg").read_text()
        source = json.loads((ROOT / "modules/net-snmp/5.9.3.sonic.1/source.json").read_text())
        path = "/debian/pool/main/n/net-snmp/net-snmp_5.9.3+dfsg.orig.tar.xz"
        origin = "https://packages.trafficmanager.net/public" + path
        cdn = "https://deb.debian.org" + path
        self.assertEqual(source["url"], origin)
        self.assertEqual(source["integrity"], "sha256-t4+TJ2qA1Acm2UlWqn0G/YdStcBiSvW78VXLwz/VIdE=")
        self.assertEqual(candidates(public, origin), [cdn, origin])
        combined = MIRRORS.configuration(public, ENVIRONMENT)
        self.assertEqual(candidates(combined, origin),
                         ["https://private-mirror.example.test" + path, cdn, origin])
        for environment in ({}, {"DEBIAN_SECURITY_MIRROR_ROOT": ENVIRONMENT["DEBIAN_SECURITY_MIRROR_ROOT"]}):
            with self.subTest(environment=sorted(environment)):
                self.assertEqual(candidates(MIRRORS.configuration(public, environment), origin), [cdn, origin])
        for other in (origin.replace("5.9.3", "5.9.4"), origin.replace("+dfsg", "dfsg"),
                      origin.replace("+dfsg", "3dfsg"), origin + "?query", origin + ".sig",
                      origin.replace("packages.trafficmanager.net", "another.example.test")):
            with self.subTest(other=other):
                self.assertEqual(candidates(public, other), [])
                self.assertEqual(candidates(combined, other), [])

    def test_net_snmp_packaging_alias_preserves_exact_checksum_and_fallbacks(self):
        public = (ROOT / "ci/source_mirrors.cfg").read_text()
        path = "/debian/pool/main/n/net-snmp/net-snmp_5.9.3+dfsg-2+deb12u1.debian.tar.xz"
        origin = "https://packages.trafficmanager.net/public" + path
        cdn = "https://deb.debian.org" + path
        checksum = "42bfdc8dff259be56735b0d48a4cbd85f45ff40d0bea86fceaf88ba7a6dc735f"
        for relative in ("MODULE.bazel", "overlay/MODULE.bazel"):
            module = (ROOT / "modules/net-snmp/5.9.3.sonic.1" / relative).read_text()
            self.assertIn('urls = ["' + origin + '"]', module)
            self.assertIn('sha256 = "' + checksum + '"', module)
        self.assertEqual(candidates(public, origin), [cdn, origin])
        combined = MIRRORS.configuration(public, ENVIRONMENT)
        self.assertEqual(candidates(combined, origin),
                         ["https://private-mirror.example.test" + path, cdn, origin])
        for environment in ({}, {"DEBIAN_SECURITY_MIRROR_ROOT": ENVIRONMENT["DEBIAN_SECURITY_MIRROR_ROOT"]}):
            with self.subTest(environment=sorted(environment)):
                self.assertEqual(candidates(MIRRORS.configuration(public, environment), origin), [cdn, origin])
        for other in (origin.replace("5.9.3", "5.9.4"), origin.replace("deb12u1", "deb12u2"),
                      origin.replace("+dfsg", "dfsg"), origin.replace("+dfsg", "3dfsg"),
                      origin.replace("+deb12", "deb12"), origin.replace("+deb12", "2deb12"),
                      origin + "?query", origin + ".sig", origin.replace(".debian.tar", ".orig.tar"),
                      origin.replace("packages.trafficmanager.net", "another.example.test")):
            with self.subTest(other=other):
                self.assertEqual(candidates(public, other), [])
                self.assertEqual(candidates(combined, other), [])

    def test_snapshot_file_objects_use_the_private_content_address(self):
        cfg = MIRRORS.configuration("", ENVIRONMENT)
        digest = "3e383bbe88cbed56bdad4ba655c40abf0e961cf7"
        source = "https://snapshot.debian.org/file/" + digest
        self.assertEqual(candidates(cfg, source), ["https://private-mirror.example.test/file/" + digest, source])
        for url in (source + "?q=1", source[:-1], source.replace("snapshot.debian.org", "malicious.invalid")):
            self.assertEqual(candidates(cfg, url), [])

    def test_invalid_secret_values_are_rejected_without_echo(self):
        key = "DEBIAN_MIRROR_ROOT"
        for value in (ENVIRONMENT[key].replace("https:", "http:"),
                      ENVIRONMENT[key].replace("https://", "https://user:password@"),
                      ENVIRONMENT[key] + "?query", ENVIRONMENT[key] + "\nblock *",
                      ENVIRONMENT[key] + "20200102T030405Z/",
                      ENVIRONMENT[key].replace("/debian/", "/debian-security/")):
            with self.subTest(value=value), self.assertRaises(ValueError) as error:
                MIRRORS.selected_mirrors({key: value})
            self.assertNotIn(value, str(error.exception))
        self.assertEqual(MIRRORS.selected_mirrors(ENVIRONMENT), ENVIRONMENT)

    def test_final_public_downloader_override_is_respected(self):
        command = [MIRRORS.DOWNLOADER_ARG + "/first.cfg", "--module=example",
                   MIRRORS.DOWNLOADER_ARG + "/selected.cfg"]
        self.assertEqual(MIRRORS.public_configuration(command, Path("default.cfg")), Path("/selected.cfg"))

    def test_explicit_probe_cannot_pass_without_both_secrets(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, "Both.*secrets"):
                MIRRORS.probe(SimpleNamespace(artifacts=Path(temporary)), {}, MIRRORS.Redactor([]))


class PrivateMirrorWrapperTest(unittest.TestCase):
    def exercise(self, code=0, binary_leak=False, enabled=True):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            artifacts = work / "artifacts"
            artifacts.mkdir()
            child = work / "child.py"
            child.write_text(
                "import json,os,pathlib,re,sys\n"
                "assert 'DEBIAN_MIRROR_ROOT' not in os.environ\n"
                "assert 'DEBIAN_SECURITY_MIRROR_ROOT' not in os.environ\n"
                f"artifacts=pathlib.Path({str(artifacts)!r})\n"
                "flags=[a for a in sys.argv if a.startswith('--bazel-build-arg=--experimental_downloader_config=')]\n"
                "if flags:\n"
                " config=pathlib.Path(flags[-1].split('=',2)[2])\n"
                " assert config.stat().st_mode & 0o777 == 0o600\n"
                " location=re.search(r'https://private-mirror[^ ]+',config.read_text()).group(0)\n"
                " print(location, flush=True)\n"
                " print('private-mirror.example.test',file=sys.stderr)\n"
                " (artifacts/'build.log').write_text(location+'\\nprivate-mirror.example.test')\n"
                f" if {binary_leak!r}: (artifacts/'payload.so').write_bytes(b'\\x00'+location.encode())\n"
                f"sys.exit({code})\n")
            environment = {k: v for k, v in os.environ.items() if k not in ENVIRONMENT}
            if enabled:
                environment.update(ENVIRONMENT)
            environment.pop("GITHUB_ACTIONS", None)
            result = subprocess.run([sys.executable, str(ROOT / "ci/private_mirrors.py"), "run",
                                     "--artifacts", str(artifacts), "--private-dir", str(work / "private"),
                                     "--public-config", str(ROOT / "ci/source_mirrors.cfg"),
                                     "--", sys.executable, str(child)], env=environment,
                                    capture_output=True, text=True, timeout=30)
            self.assertNotIn("private-mirror.example.test", result.stdout + result.stderr)
            self.assertEqual(list((work / "private").glob("mirror-*")), [])
            if enabled and not binary_leak:
                self.assertEqual(result.returncode, code, result.stdout + result.stderr)
                self.assertNotIn("private-mirror.example.test", (artifacts / "build.log").read_text())
                receipt = json.loads((artifacts / "private-mirrors.json").read_text())
                self.assertTrue(receipt["public_fallback"])
            if binary_leak:
                self.assertIn("Private mirror location remains", result.stderr)
                self.assertIn(b"private-mirror.example.test", (artifacts / "payload.so").read_bytes())
            return result

    def test_success_and_failed_build_both_scrub_output_and_remove_config(self):
        for code in (0, 9):
            result = self.exercise(code=code)
            self.assertEqual(result.returncode, code, result.stdout + result.stderr)

    def test_binary_payload_leak_fails_instead_of_rewriting_payload(self):
        self.assertNotEqual(self.exercise(binary_leak=True).returncode, 0)

    def test_no_secret_keeps_public_command_usable(self):
        self.assertEqual(self.exercise(enabled=False).returncode, 0)


@unittest.skipUnless(os.environ.get("REGISTRY_CI_TEST_BAZEL"), "requires real Bazel download integration")
class PrivateMirrorBazelTest(unittest.TestCase):
    # Bazel 8.5 resolves these implicit module dependencies before fetching even
    # a single http_file. None is used by the builtin http_file repository rule;
    # empty local modules keep this transport test independent of BCR and its
    # transitive dependencies. An empty registry and non-loopback download deny
    # rule make a new, unaccounted dependency fail instead of using the network.
    UNUSED_BUILTIN_MODULES = (
        "bazel_features", "buildozer", "platforms", "protobuf", "rules_cc",
        "rules_java", "rules_license", "rules_proto", "rules_python",
        "rules_shell", "zlib",
    )

    def test_first_choice_missing_corrupt_and_unrecoverable_packages(self):
        self.exercise_downloads(
            "https://snapshot.debian.org/archive/debian/" + MANIFEST["debian"]["current"] +
            "/pool/main/f/foo/foo_1_amd64.deb",
            (("valid", "valid"), ("missing", "valid"), ("corrupt", "valid"), ("corrupt", "corrupt")))

    def test_cdn_origin_uses_private_before_public_fallback(self):
        self.exercise_downloads(
            "https://deb.debian.org/debian/pool/main/f/foo/foo_1_amd64.deb",
            (("valid", "valid"), ("missing", "valid")))

    def test_historical_and_cdn_source_archives_fetch_privately(self):
        for original in (
            "https://snapshot.debian.org/archive/debian/20241222T205329Z/pool/main/s/socat/socat_1.8.0.2.orig.tar.bz2",
            "https://deb.debian.org/debian/pool/main/libn/libnl3/libnl3_3.7.0-0.2.debian.tar.xz",
        ):
            self.exercise_downloads(original, (("valid", "valid"),))

    def exercise_downloads(self, original, cases):
        payload = b"locked Debian fixture bytes\n"
        checksum = hashlib.sha256(payload).hexdigest()
        for primary, fallback in cases:
            with self.subTest(primary=primary, fallback=fallback), tempfile.TemporaryDirectory() as temporary:
                work = Path(temporary)
                requests = []

                class Handler(BaseHTTPRequestHandler):
                    def do_GET(self):
                        requests.append(self.path)
                        behavior = primary if self.path.startswith("/private/") else fallback
                        if behavior == "missing":
                            self.send_error(404)
                            return
                        data = payload if behavior == "valid" else b"wrong package bytes"
                        self.send_response(200)
                        self.send_header("Content-Length", str(len(data)))
                        self.end_headers()
                        self.wfile.write(data)

                    def log_message(self, *_args):
                        pass

                server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
                threading.Thread(target=server.serve_forever, daemon=True).start()
                try:
                    local = f"http://127.0.0.1:{server.server_port}"
                    public = f"rewrite {re.escape(original.removeprefix('https://'))} {local}/public/package\n"
                    public += (ROOT / "ci/source_mirrors.cfg").read_text()
                    config = work / "downloader.cfg"
                    config.write_text(MIRRORS.configuration(public, {"DEBIAN_MIRROR_ROOT": local + "/private/archive/debian/"})
                                      + "block *\nallow 127.0.0.1\n")
                    module = (
                        'module(name="mirror_test")\n'
                        'http_file=use_repo_rule("@bazel_tools//tools/build_defs/repo:http.bzl","http_file")\n')
                    # Registry access itself uses only this empty local tree.
                    # No pre-existing registry or repository cache can mask a
                    # missing dependency or change the HTTP candidate sequence.
                    registry = work / "empty-registry"
                    registry.mkdir()
                    for name in self.UNUSED_BUILTIN_MODULES:
                        stub = work / "unused-modules" / name
                        stub.mkdir(parents=True)
                        (stub / "MODULE.bazel").write_text(f'module(name={name!r})\n')
                        module += f'local_path_override(module_name={name!r},path={str(stub)!r})\n'
                    (work / "MODULE.bazel").write_text(module +
                        f'http_file(name="package",urls=[{original!r}],sha256={checksum!r})\n')
                    (work / "BUILD.bazel").write_text("")
                    cache = work / "cache"
                    result = subprocess.run([os.environ["REGISTRY_CI_TEST_BAZEL"], "--batch", "--ignore_all_rc_files",
                                             f"--output_user_root={work / 'bazel'}", "fetch", "--repo=@package",
                                             f"--registry={registry.as_uri()}", f"--repository_cache={cache}",
                                             f"--experimental_downloader_config={config}",
                                             "--http_connector_attempts=1", "--lockfile_mode=update"],
                                            cwd=work, capture_output=True, text=True, timeout=180)
                    order = list(dict.fromkeys(path.split('/')[1] for path in requests))
                    self.assertEqual(order, ["private"] if primary == "valid" else ["private", "public"], result.stderr)
                    cached = cache / "content_addressable/sha256" / checksum / "file"
                    if fallback == "corrupt":
                        self.assertNotEqual(result.returncode, 0)
                        self.assertFalse(cached.exists())
                    else:
                        self.assertEqual(result.returncode, 0, result.stderr)
                        self.assertEqual(cached.read_bytes(), payload)
                finally:
                    server.shutdown()
                    server.server_close()


if __name__ == "__main__":
    unittest.main()
