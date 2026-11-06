"""The Java observer must preserve transport and publish only sanitized evidence."""
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import shutil
import ssl
import subprocess
import tempfile
import threading
import time
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[2]
PRIVATE_HOST = "mirror.fixture.invalid"
PUBLIC_HOST = "deb.debian.org"
EXTERNAL_HOST = "external.fixture.invalid"
STAMP = "20260727T143429Z"
PAYLOAD = b"checksum-verified fixture bytes\n"
SHA256 = hashlib.sha256(PAYLOAD).hexdigest()


class DebianHttpAuditTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.java = shutil.which("java")
        if not cls.java or not shutil.which("openssl"):
            raise unittest.SkipTest("Java and openssl are needed for the HTTP observer fixture")
        cls.temporary = tempfile.TemporaryDirectory(prefix="debian-http-audit-")
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.build = Path(cls.temporary.name)
        classes = cls.build / "classes"
        classes.mkdir()
        provided = os.environ.get("REGISTRY_CI_HTTP_AUDIT_FIXTURE_JAR")
        sources = [str(ROOT / "ci/tests/fixtures/HttpAuditProbe.java")]
        if not provided:
            sources.append(str(ROOT / "ci/DebianHttpAudit.java"))
        compiler = [shutil.which("javac")] if shutil.which("javac") else [
            cls.java, "-m", "jdk.compiler/com.sun.tools.javac.Main"]
        result = subprocess.run([*compiler, "-source", "11", "-target", "11", "-d", str(classes),
                                 *sources],
                                capture_output=True, text=True, timeout=60)
        if result.returncode:
            raise AssertionError("Java observer fixture compilation failed:\n" + result.stderr)
        cls.classes = classes
        cls.agent = Path(provided) if provided else cls.build / "observer.jar"
        cls.seed = cls.build / "seed.jar"
        jars = [(cls.seed, "HttpAuditProbe$Seed", "HttpAuditProbe*.class")]
        if provided:
            with zipfile.ZipFile(cls.agent) as archive:
                expected = hashlib.sha256((ROOT / "ci/DebianHttpAudit.java").read_bytes()).hexdigest().encode("ascii")
                if archive.read("META-INF/sonic-debian-http-audit.sha256") != expected:
                    raise AssertionError("Provided HTTP observer does not match the maintained source")
        else:
            jars.append((cls.agent, "DebianHttpAudit", "DebianHttpAudit*.class"))
        for jar, main, pattern in jars:
            with zipfile.ZipFile(jar, "w") as archive:
                archive.writestr("META-INF/MANIFEST.MF", f"Manifest-Version: 1.0\nPremain-Class: {main}\n\n")
                for source in classes.glob(pattern):
                    archive.write(source, source.name)
        cls.certificate, cls.key, cls.trust = (cls.build / name for name in ("fixture.crt", "fixture.key", "fixture.p12"))
        subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1",
                        "-keyout", str(cls.key), "-out", str(cls.certificate), "-subj", "/CN=fixture",
                        "-addext", f"subjectAltName=DNS:{PRIVATE_HOST},DNS:{PUBLIC_HOST},DNS:{EXTERNAL_HOST},IP:127.0.0.1"],
                       capture_output=True, check=True, timeout=30)
        subprocess.run([cls.java, "-m", "java.base/sun.security.tools.keytool.Main", "-importcert",
                        "-noprompt", "-alias", "fixture", "-file", str(cls.certificate), "-keystore",
                        str(cls.trust), "-storepass", "fixture-only"], capture_output=True, check=True, timeout=30)
        cls.hosts = cls.build / "hosts"
        cls.hosts.write_text(f"127.0.0.1 {PRIVATE_HOST} {PUBLIC_HOST} {EXTERNAL_HOST}\n")
        cls.jvm = [f"-Djdk.net.hosts.file={cls.hosts}", f"-Djavax.net.ssl.trustStore={cls.trust}",
                   "-Djavax.net.ssl.trustStorePassword=fixture-only"]
        cls.env = {k: v for k, v in os.environ.items() if k.lower() not in
                   ("http_proxy", "https_proxy", "all_proxy", "no_proxy")}

    def setUp(self):
        self.work = Path(tempfile.mkdtemp(prefix="case-", dir=self.build))
        self.mode = "success"
        self.requests = []
        test = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                private = self.server is test.private
                test.requests.append(("private" if private else "public", self.path, self.headers.get("Cookie")))
                if private and test.mode == "missing":
                    self.send_error(404)
                    return
                if private and test.mode in ("redirect", "official-redirect"):
                    self.send_response(302)
                    host = PUBLIC_HOST if test.mode == "official-redirect" else EXTERNAL_HOST
                    self.send_header("Location", f"https://{host}:{test.public.server_port}/opaque-target?sentinel-query")
                    self.end_headers()
                    return
                body = b"wrong checksum" if test.mode == "all-bad" or (private and test.mode == "corrupt") else PAYLOAD
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Set-Cookie", "fixture-cookie=sentinel-cookie")
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_args):
                pass

        self.private = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.public = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        for server in (self.private, self.public):
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(self.certificate, self.key)
            server.socket = context.wrap_socket(server.socket, server_side=True)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            self.addCleanup(server.server_close)
            self.addCleanup(server.shutdown)
        self.base = f"https://{PRIVATE_HOST}:{self.private.server_port}/private-mount/archive/debian/{STAMP}/"
        self.url = self.base + "pool/main/f/fixture/fixture_1_amd64.deb?sentinel-query"
        self.output = self.work / "evidence-ü"
        self.output.mkdir()
        self.properties = self.work / "private.properties"
        self.properties.write_text(f"output={self.output}\nmirror.0={self.base}\n", encoding="utf-8")
        self.properties.chmod(0o600)

    def records(self):
        return [json.loads(line) for path in self.output.glob("http-*.jsonl")
                for line in path.read_text().splitlines()]

    def run_probe(self, *arguments, delegate=False):
        command = [self.java, *self.jvm]
        if delegate:
            command += [f"-javaagent:{self.seed}"]
        command += [f"-javaagent:{self.agent}={self.properties}", "-cp", str(self.classes),
                    "HttpAuditProbe", *map(str, arguments)]
        return subprocess.run(command, capture_output=True, text=True, timeout=30, env=self.env)

    def assert_private(self):
        encoded = json.dumps(self.records())
        for value in (PRIVATE_HOST, "private-mount", "sentinel-query", "sentinel-cookie", EXTERNAL_HOST, "opaque-target"):
            self.assertNotIn(value, encoded)
        for path in self.output.glob("http-*.jsonl"):
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_private_https_and_fast_jvm_health(self):
        result = self.run_probe("fetch", self.url)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([(r["origin"], r["type"], r["status"]) for r in self.records() if r["event"] == "response"],
                         [("private", "binary", 200)])
        self.assertEqual(self.records()[-1]["event"], "shutdown")
        self.assertFalse(self.records()[-1]["recording_failed"])
        self.assert_private()

    def test_existing_handler_cookies_and_exact_exceptions_preserved(self):
        result = self.run_probe("delegate", self.url, delegate=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.requests[0][2], "fixture-cookie=sentinel-cookie")
        self.assertTrue(self.records()[0]["had_delegate"])
        self.assert_private()

    def test_proxy_connect_acknowledgement_is_not_an_object_response(self):
        result = self.run_probe("proxy-callbacks", self.url, delegate=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        transport = [r for r in self.records() if r["event"] in ("request", "response")]
        self.assertEqual([r["event"] for r in transport], ["request", "response"])
        self.assertEqual(transport[1]["status"], 404)
        self.assertFalse(self.records()[-1]["recording_failed"])
        self.assert_private()

    def test_external_redirect_has_origin_and_initiating_object_only(self):
        self.check_redirect("redirect")

    def test_official_debian_redirect_keeps_the_original_index_identity(self):
        self.check_redirect("official-redirect")

    def check_redirect(self, mode):
        self.mode = mode
        result = self.run_probe("fetch", self.url)
        self.assertEqual(result.returncode, 0, result.stderr)
        responses = [r for r in self.records() if r["event"] == "response"]
        self.assertEqual([(r["origin"], r["status"]) for r in responses], [("private", 302), ("public", 200)])
        self.assertNotIn("path", responses[1])
        self.assertEqual(responses[1]["type"], "redirect")
        self.assertEqual(responses[1]["object"], f"/archive/debian/{STAMP}/pool/main/f/fixture/fixture_1_amd64.deb")
        self.assert_private()

    def test_loopback_controls_are_ignored_and_historical_objects_classified(self):
        origin = self.base.split("/archive/", 1)[0]
        result = self.run_probe("callbacks", "http://localhost/ignored.deb", "http://127.0.0.1/ignored.udeb",
                                "http://[::1]/ignored.ddeb", origin + "/file/" + "a" * 40,
                                origin + "/archive/debian/20241222T205329Z/dists/trixie/InRelease",
                                origin + "/debian/pool/main/f/fixture/fixture_1.orig.tar.xz",
                                "https://deb.debian.org/debian/pool/main/f/fixture/fixture_1_amd64.deb")
        self.assertEqual(result.returncode, 0, result.stderr)
        responses = [r for r in self.records() if r["event"] == "response"]
        self.assertEqual([(r["origin"], r["type"]) for r in responses],
                         [("private", "content-addressed"), ("private", "index"), ("private", "source"), ("public", "binary")])
        self.assert_private()

    def test_explicitly_configured_loopback_origin_is_observed(self):
        base = self.base.replace(PRIVATE_HOST, "127.0.0.1")
        self.properties.write_text(f"output={self.output}\nmirror.0={base}\n", encoding="utf-8")
        result = self.run_probe("fetch", self.url.replace(PRIVATE_HOST, "127.0.0.1"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([r["origin"] for r in self.records() if r["event"] == "response"], ["private"])

    def test_recorder_failure_does_not_change_download_and_is_sticky(self):
        result = self.run_probe("fault", self.url, self.output)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(self.requests), 2)
        health = [r for r in self.records() if r["event"] in ("health", "shutdown")]
        self.assertEqual(len(health), 2)
        self.assertTrue(all(r["recording_failed"] for r in health))

    def test_replaced_handler_is_reported_unhealthy(self):
        result = self.run_probe("replace", self.url, self.output)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(next(r for r in self.records() if r["event"] == "health")["handler_still_installed"])

    def test_flush_confirms_live_jvm_without_shutdown(self):
        exit_file = self.work / "exit"
        command = [self.java, *self.jvm, f"-javaagent:{self.agent}={self.properties}", "-cp", str(self.classes),
                   "HttpAuditProbe", "hold", self.url, str(exit_file)]
        with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=self.env) as process:
            self.assertEqual(process.stdout.readline().strip(), "ready")
            (self.output / "flush").touch()
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline and not any(r["event"] == "health" for r in self.records()):
                time.sleep(0.05)
            self.assertIsNone(process.poll())
            health = [r for r in self.records() if r["event"] == "health"]
            self.assertEqual(len(health), 1)
            self.assertTrue(health[0]["handler_still_installed"])
            self.assertFalse(health[0]["recording_failed"])
            exit_file.touch()
            _, stderr = process.communicate(timeout=5)
            self.assertEqual(process.returncode, 0, stderr)

    def test_fast_no_transfer_and_failed_initialization_keep_original_exit(self):
        result = self.run_probe("fast")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([r["event"] for r in self.records()], ["installed", "shutdown"])
        self.properties.write_text("output=not-absolute\nmirror.0=private-invalid-value\n")
        result = self.run_probe("fetch", self.url)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("observation is incomplete", result.stderr)
        self.assertNotIn("private-invalid-value", result.stderr)

    @unittest.skipUnless(os.environ.get("REGISTRY_CI_HTTP_AUDIT_FIXTURE_BAZEL") or os.environ.get("REGISTRY_CI_TEST_BAZEL"),
                         "requires real Bazel download integration")
    def test_real_bazel_opaque_fallback_redirect_integrity_and_cache(self):
        # Stub unused implicit modules, including their extension symbols, so even
        # mod graph --extension_info=all requires no registry/source networking.
        modules = ["bazel_features", "buildozer", "platforms", "protobuf", "rules_cc", "rules_java",
                   "rules_license", "rules_proto", "rules_python", "rules_shell", "zlib"]
        module = ['module(name="http_audit_fixture")']
        for name in modules:
            stub = self.work / "unused" / name
            stub.mkdir(parents=True)
            (stub / "MODULE.bazel").write_text(f"module(name={name!r})\n")
            (stub / "BUILD.bazel").write_text("")
            module.append(f"local_path_override(module_name={name!r},path={str(stub)!r})")
        stub_extension = ('def _repo(ctx):\n    ctx.file("BUILD.bazel", "")\n'
                          'repo = repository_rule(implementation=_repo)\n'
                          'def _extension(ctx):\n    for name in REPOSITORIES:\n        repo(name=name)\n'
                          'EXTENSION = module_extension(implementation=_extension)\n')
        java_stub = self.work / "unused/rules_java/java"
        java_stub.mkdir()
        (java_stub / "BUILD.bazel").write_text("")
        (java_stub / "extensions.bzl").write_text(stub_extension.replace("REPOSITORIES", repr([
            "local_jdk", "remote_java_tools", "remote_java_tools_linux", "remote_java_tools_windows",
            "remote_java_tools_darwin_x86_64", "remote_java_tools_darwin_arm64"])).replace("EXTENSION", "toolchains"))
        (self.work / "unused/buildozer/buildozer_binary.bzl").write_text(stub_extension.replace(
            "REPOSITORIES", '["buildozer_binary"]').replace("EXTENSION", "buildozer_binary"))
        module += ['audit=use_extension("//:extension.bzl","audit")', 'use_repo(audit,"observed")']
        (self.work / "MODULE.bazel").write_text("\n".join(module) + "\n")
        (self.work / "BUILD.bazel").write_text("")
        registry = self.work / "empty-registry"
        registry.mkdir()
        suffix = "pool/main/f/fixture/fixture_1_amd64.deb"
        original = f"https://{PUBLIC_HOST}/debian/{suffix}"
        config = self.work / "downloader.cfg"
        pattern = re.escape(original.split("://", 1)[1])
        config.write_text(f"rewrite {pattern} {self.base}{suffix}\n"
                          f"rewrite {pattern} https://{PUBLIC_HOST}:{self.public.server_port}/debian/{suffix}\n"
                          f"block *\nallow {PRIVATE_HOST}\nallow {PUBLIC_HOST}\n")
        extension = ('def _repo(ctx):\n    ctx.file("BUILD.bazel", "")\n'
                     'repo=repository_rule(implementation=_repo)\n'
                     'def _extension(ctx):\n    print("audit-fixture-download-reached")\n'
                     f'    ctx.download(url={original!r},sha256={SHA256!r},output="payload")\n'
                     '    repo(name="observed")\n'
                     'audit=module_extension(implementation=_extension)\n')
        source = self.work / "extension.bzl"
        bazel = os.environ.get("REGISTRY_CI_HTTP_AUDIT_FIXTURE_BAZEL") or os.environ["REGISTRY_CI_TEST_BAZEL"]
        prefix = [bazel, "--ignore_all_rc_files",
                  f"--output_user_root={self.work / 'bazel'}",
                  f"--host_jvm_args=-javaagent:{self.agent}={self.properties}",
                  *["--host_jvm_args=" + arg for arg in self.jvm]]
        network = [f"--registry={registry.as_uri()}", f"--downloader_config={config}"]
        common = ["mod", "graph", "--extension_info=all", *network,
                  "--http_connector_attempts=1", "--lockfile_mode=update", "--color=no", "--curses=no",
                  f"--build_event_json_file={self.work / 'absent-events.jsonl'}"]
        try:
            first_pid = None
            for mode, expected in (("success", [("private", 200)]),
                                   ("missing", [("private", 404), ("public", 200)]),
                                   ("corrupt", [("private", 200), ("public", 200)]),
                                   ("redirect", [("private", 302), ("public", 200)]),
                                   ("all-bad", [("private", 200), ("public", 200)])):
                with self.subTest(mode=mode):
                    self.mode = mode
                    source.write_text(extension + "# " + mode + "\n")
                    before = len(self.records())
                    result = subprocess.run([*prefix, *common, "--repository_cache="], cwd=self.work,
                                            capture_output=True, text=True, env=self.env, timeout=90)
                    if mode == "all-bad":
                        self.assertNotEqual(result.returncode, 0)
                    else:
                        self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn("audit-fixture-download-reached", result.stdout + result.stderr)
                    self.assertFalse((self.work / "absent-events.jsonl").exists())
                    responses = [r for r in self.records()[before:] if r["event"] == "response"]
                    self.assertEqual([(r["origin"], r["status"]) for r in responses], expected)
                    if first_pid is None:
                        first_pid = subprocess.run([*prefix, "info", "server_pid", *network], cwd=self.work,
                                                   capture_output=True, text=True, env=self.env, timeout=30).stdout.strip()
            self.mode = "success"
            for revision in ("cache-fill", "cache-read"):
                source.write_text(extension + "# " + revision + "\n")
                before, before_requests = len(self.records()), len(self.requests)
                result = subprocess.run([*prefix, *common, f"--repository_cache={self.work / 'cache'}"],
                                        cwd=self.work, capture_output=True, text=True, env=self.env, timeout=90)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("audit-fixture-download-reached", result.stdout + result.stderr)
                if revision == "cache-read":
                    self.assertEqual(self.requests[before_requests:], [])
                    self.assertEqual(self.records()[before:], [])
            final_pid = subprocess.run([*prefix, "info", "server_pid", *network], cwd=self.work,
                                       capture_output=True, text=True, env=self.env, timeout=30).stdout.strip()
            self.assertTrue(first_pid)
            self.assertEqual(first_pid, final_pid)
            (self.output / "flush").touch()
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline and not any(r["event"] == "health" for r in self.records()):
                time.sleep(0.05)
            health = [r for r in self.records() if r["event"] == "health"]
            self.assertEqual(len(health), 1)
            self.assertTrue(health[0]["handler_still_installed"])
            self.assertFalse(health[0]["recording_failed"])
            self.assert_private()
        finally:
            subprocess.run([*prefix, "shutdown"], cwd=self.work, capture_output=True,
                           env=self.env, timeout=30)


if __name__ == "__main__":
    unittest.main()
