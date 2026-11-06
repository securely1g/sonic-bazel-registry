#!/usr/bin/env python3
"""Run the checked Common helper against a signed local APT fixture in a container.

The fixture directory contains the original helper/lock, its selected real DEBs,
a signed repository under repo/, trusted.gpg, and a loopback TLS certificate/key.
Run with no external network and snapshot.debian.org mapped to 127.0.0.1.
"""

import argparse
import functools
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
import os
from pathlib import Path
import socket
import ssl
import subprocess
import sys
import threading
from urllib.parse import urlsplit


OWNER_SHA256 = "8302de9c34064c4256e881d5ffd32ea8cd2d0efbdda9a78a11da6444055b899d"
EXPECTED = {"libboost-serialization1.83.0", "libhiredis1.1.0", "libnorm1t64",
            "libpgm-5.3-0t64", "libsodium23", "libzmq5"}


class Handler(SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):
        pass

    def do_GET(self):
        failure = self.server.role == "private" and self.server.scenario == "fallback"
        corrupt = self.server.scenario == "corrupt" and self.path.endswith(".deb")
        if failure:
            self.server.events.append({"origin": self.server.role, "path": self.path, "status": 503})
            self.send_error(503)
        elif corrupt:
            original = Path(self.translate_path(self.path)).read_bytes()
            data = bytes([original[0] ^ 1]) + original[1:]
            self.server.events.append({"origin": self.server.role, "path": self.path, "status": 200})
            self.send_response(200)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        else:
            self.server.events.append({"origin": self.server.role, "path": self.path,
                                       "status": 200 if Path(self.translate_path(self.path)).is_file() else 404})
            super().do_GET()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--scenario", choices=("private", "fallback", "corrupt"), required=True)
    parser.add_argument("--image-reference", required=True)
    args = parser.parse_args()
    fixture, output = args.fixture, args.output
    output.mkdir(parents=True, exist_ok=True)
    assert {r[4][0] for r in socket.getaddrinfo("snapshot.debian.org", 443)} <= {"127.0.0.1", "::1"}
    for key in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "all_proxy"):
        os.environ.pop(key, None)
    config = Path("/tmp/apt-signed-fixture.conf")
    trust_parts = Path("/tmp/apt-signed-fixture-trusted.d")
    trust_parts.mkdir(exist_ok=True)
    config.write_text(f'''Acquire::http::Proxy "DIRECT";
Acquire::https::Proxy "DIRECT";
Acquire::https::CaInfo "{fixture / 'tls.crt'}";
Acquire::Retries "0";
Acquire::https::Timeout "5";
Acquire::Languages "none";
Dir::Etc::trusted "{fixture / 'trusted.gpg'}";
Dir::Etc::trustedparts "{trust_parts}";
''')
    os.environ["APT_CONFIG"] = str(config)
    spec = importlib.util.spec_from_file_location("apt_runtime_mirrors", Path(__file__).parents[1] / "apt_runtime_mirrors.py")
    adapter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter)
    script = fixture / "test-runtime-prepare.py"
    lock = fixture / "test-runtime.MODULE.bazel.lock"
    owner = adapter.load_owner(script, OWNER_SHA256)
    owner["require_container"]()
    owner["require_no_installed_common"]()
    selected = owner["select_runtime"](json.loads(lock.read_text()), "amd64")
    before = owner["inventory"]()
    assert {p.split(":")[0] for p in owner["missing_packages"](selected, before)} == EXPECTED
    mapping = {adapter.snapshot_base(p["urls"][0]): "https://127.0.0.1:8443" +
               urlsplit(adapter.snapshot_base(p["urls"][0])).path for p in selected.values()}
    mirror_config = Path("/tmp/signed-fixture-mirrors.json")
    mirror_config.write_text(json.dumps({"schema_version": 1, "mirrors": mapping}))
    mirror_config.chmod(0o600)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(fixture / "tls.crt", fixture / "tls.key")
    events, servers = [], []
    for role, port in (("private", 8443), ("public", 443)):
        server = ThreadingHTTPServer(("127.0.0.1", port), functools.partial(Handler, directory=str(fixture / "repo")))
        server.socket = context.wrap_socket(server.socket, server_side=True)
        server.role, server.scenario, server.events = role, args.scenario, events
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        servers.append(server)
    result = {"scenario": args.scenario, "result": "incomplete"}
    try:
        failed = False
        try:
            receipt = adapter.prepare(owner, lock, mirror_config, output / "preparation.apt.log",
                                      output / "preparation.json", "amd64")
        except subprocess.CalledProcessError:
            failed = True
            if args.scenario != "corrupt":
                raise
        if args.scenario == "corrupt":
            assert failed, "Corrupted packages unexpectedly installed"
            assert "Hash Sum mismatch" in (output / "preparation.apt.log").read_text()
            assert owner["inventory"]() == before, "Corruption changed the installed package inventory"
            result["corrupt_package_rejected_before_install"] = True
        else:
            assert not failed
            assert {p["package"] for p in receipt["verified_downloads"]} == EXPECTED
            requests_before_owner = len(events)
            owner_output = output / "owner.json"
            run = subprocess.run([sys.executable, "-B", str(script), "--lock", str(lock),
                                  "--image-reference", args.image_reference, "--output", str(owner_output)],
                                 capture_output=True, text=True)
            (output / "owner.log").write_text(run.stdout + run.stderr)
            assert run.returncode == 0, "Unchanged owner validation failed"
            assert owner_output.with_suffix(".apt.log").stat().st_size == 0
            assert len(events) == requests_before_owner, "The owner made a second APT transfer"
            owner_receipt = json.loads(owner_output.read_text())
            identity = {k: v for k, v in owner_receipt.items()
                        if k not in ("SONIC_TEST_RUNTIME_ID", "preserved_base_packages", "lock_sha256")}
            assert hashlib.sha256(json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()).hexdigest() == owner_receipt["SONIC_TEST_RUNTIME_ID"]
            acquired = [e for e in events if e["status"] == 200 and e["path"].endswith(".deb")]
            expected_origin = "private" if args.scenario == "private" else "public"
            assert len(acquired) == 6 and all(e["origin"] == expected_origin for e in acquired)
            if args.scenario == "private":
                assert not any(e["origin"] == "public" for e in events)
            else:
                assert any(e["origin"] == "private" and e["status"] == 503 for e in events)
            result.update({"verified_downloads": receipt["verified_downloads"],
                           "owner_additional_transfers": 0, "actual_deb_origin": expected_origin})
        assert hashlib.sha256(script.read_bytes()).hexdigest() == OWNER_SHA256
        result["result"] = "passed"
    finally:
        for server in servers:
            server.shutdown()
            server.server_close()
        result["actual_server_requests"] = events
        (output / "integration.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "actual_server_requests"}))


if __name__ == "__main__":
    main()
