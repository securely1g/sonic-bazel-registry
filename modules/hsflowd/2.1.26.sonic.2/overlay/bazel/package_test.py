"""Validate the installed hsflowd payload, symbols and private SONiC service."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import struct
import subprocess
import tarfile
import tempfile
import time
import zlib


MODULES = ("json", "dnssd", "sonic", "psample", "docker", "dropmon", "vpp")


def run(command, env, **kwargs):
    return subprocess.run([str(x) for x in command], env=env, check=True,
                          capture_output=True, text=True, timeout=30, **kwargs).stdout


def stop(process):
    if process is not None and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)


def wait_for(predicate, process, log, seconds=45):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise AssertionError("Service exited: " + log.read_text(errors="replace"))
        if predicate():
            return
        time.sleep(0.1)
    raise AssertionError("Service did not become ready: " + log.read_text(errors="replace"))


def decode_probe(data):
    """Decode just the original mod_json rtmetric format exercised by this test."""
    offset = 0

    def integer():
        nonlocal offset
        value = struct.unpack_from("!I", data, offset)[0]
        offset += 4
        return value

    def string():
        nonlocal offset
        length = integer()
        value = data[offset:offset + length].decode("ascii")
        offset += (length + 3) & ~3
        return value

    assert integer() == 5, "Expected an sFlow v5 datagram"
    address_type = integer()
    assert address_type in (1, 2)
    offset += 4 if address_type == 1 else 16
    subagent, sequence, uptime, count = [integer() for _ in range(4)]
    found = []
    for _ in range(count):
        tag, length = integer(), integer()
        end = offset + length
        assert end <= len(data)
        if tag == (4300 << 12) + 1002:
            datasource, fields = string(), integer()
            if datasource == "bazel_fixture":
                assert fields == 1
                name, kind, value = string(), integer(), integer()
                assert name == "probe" and kind == 1, (name, kind)
                found.append(value)
                assert offset == end
        offset = end
    assert offset == len(data)
    return found


def service_probe(root, payload, fixture, env):
    """Use real installed hsflowd, mod_sonic, mod_json, hiredis and Redis."""
    service = root / "service"
    service.mkdir()
    sock = service / "redis.sock"
    redis_log, daemon_log = service / "redis.log", service / "hsflowd.log"
    loader = fixture / "usr/lib/x86_64-linux-gnu/ld-linux-x86-64.so.2"
    if not loader.exists():
        loader = fixture / "lib/x86_64-linux-gnu/ld-linux-x86-64.so.2"
    libraries = sorted({str(p.parent) for p in fixture.rglob("*.so*") if p.is_file()})
    prefix = [loader, "--library-path", ":".join(libraries)]
    redis_server = fixture / "usr/bin/redis-server"
    redis_cli = fixture / "usr/bin/redis-cli"
    assert loader.is_file() and redis_server.is_file() and redis_cli.is_file()
    redis, daemon = None, None
    collector = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    collector.bind(("127.0.0.1", 0))
    collector.settimeout(0.3)
    fifo = service / "metrics.fifo"
    os.mkfifo(fifo, 0o600)
    fifo_fd = os.open(fifo, os.O_RDWR | os.O_NONBLOCK)
    try:
        with redis_log.open("w") as redis_output, daemon_log.open("w") as daemon_output:
            redis = subprocess.Popen([str(x) for x in [*prefix, redis_server,
                "--port", "0", "--unixsocket", sock, "--unixsocketperm", "700",
                "--save", "", "--appendonly", "no", "--dir", service,
                "--notify-keyspace-events", "Kh"]], env=env,
                stdout=redis_output, stderr=subprocess.STDOUT)
            wait_for(sock.exists, redis, redis_log, 15)

            def command(database, *args):
                return run([*prefix, redis_cli, "-s", sock, "-n", str(database), *args], env).strip()

            assert command(0, "PING") == "PONG"
            command(6, "HSET", "SYSTEM_READY|SYSTEM_STATE", "Status", "UP")
            command(4, "HSET", "DEVICE_METADATA|localhost", "mac", "02:00:00:00:00:01", "bgp_asn", "65000")
            interface = next((name for _, name in socket.if_nameindex() if name != "lo"), "lo")
            command(4, "HSET", "SFLOW|global", "admin_state", "up", "polling_interval", "5", "agent_id", interface)
            command(4, "HSET", "SFLOW_COLLECTOR|fixture", "collector_ip", "127.0.0.1",
                    "collector_port", str(collector.getsockname()[1]), "collector_vrf", "default")
            databases = {
                name: {"id": number, "separator": separator, "instance": "redis"}
                for name, number, separator in (("APPL_DB", 0, ":"), ("COUNTERS_DB", 2, ":"),
                                                ("CONFIG_DB", 4, "|"), ("STATE_DB", 6, "|"))
            }
            config_json = service / "database_config.json"
            config_json.write_text(json.dumps({"INSTANCES": {"redis": {
                "hostname": "127.0.0.1", "port": 0, "unix_socket_path": str(sock)}}, "DATABASES": databases}))
            config = service / "hsflowd.conf"
            config.write_text("sflow {\n sonic { dbconfig=" + str(config_json) +
                              " unixsock=on waitReady=1 suppressOther=off }\n json { fifo=" + str(fifo) + " }\n}\n")
            automatic = service / "hsflowd.auto"
            target_env = dict(env, LD_LIBRARY_PATH=str(payload / "usr/lib/x86_64-linux-gnu"))
            daemon = subprocess.Popen([str(x) for x in [payload / "usr/sbin/hsflowd",
                "-d", "-d", "-d", "-P", "-f", config, "-l", payload / "etc/hsflowd/modules",
                "-p", service / "hsflowd.pid", "-o", automatic]], env=target_env,
                stdout=daemon_output, stderr=subprocess.STDOUT)
            wait_for(lambda: automatic.exists() and "polling=5" in automatic.read_text(), daemon, daemon_log)

            def probe(value):
                message = json.dumps({"rtmetric": {"datasource": "bazel_fixture",
                    "probe": {"type": "counter32", "value": value}}}).encode()
                deadline = time.monotonic() + 12
                while time.monotonic() < deadline:
                    assert daemon.poll() is None, daemon_log.read_text(errors="replace")
                    os.write(fifo_fd, message)
                    try:
                        data, _ = collector.recvfrom(65536)
                    except socket.timeout:
                        continue
                    if value in decode_probe(data):
                        return hashlib.sha256(data).hexdigest()
                raise AssertionError("No decoded rtmetric from installed daemon: " + daemon_log.read_text(errors="replace"))

            first = probe(42)
            # Exercise the actual Redis subscription and dynamic configuration path.
            command(4, "HSET", "SFLOW|global", "polling_interval", "7")
            wait_for(lambda: "polling=7" in automatic.read_text(), daemon, daemon_log)
            second = probe(84)
            assert daemon.poll() is None
            return {"redis": "private Unix socket", "polling_change": [5, 7],
                    "rtmetric_values": [42, 84], "datagram_sha256": [first, second],
                    "scope": "Installed SONiC configuration and JSON-to-sFlow UDP paths; no kernel, VPP or ASIC sampling claim"}
    finally:
        stop(daemon)
        stop(redis)
        os.close(fifo_fd)
        collector.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("runtime", "debug", "metadata", "fixtures", "hiredis", "readelf", "objcopy", "changelog"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    args = argparse.Namespace(**{name: path.resolve(strict=True) for name, path in vars(args).items()})
    env = {k: v for k, v in os.environ.items() if k not in ("LD_LIBRARY_PATH", "LD_PRELOAD", "LD_AUDIT")}
    env.update(LC_ALL="C", TZ="UTC", DEBUGINFOD_URLS="")
    # Unix sockets have a short pathname limit; Bazel's nested test directory
    # can exceed it before the private socket name is appended.
    with tempfile.TemporaryDirectory(prefix="hsflowd-installed-", dir="/tmp") as temporary:
        root = Path(temporary)
        payload, debug, empty, fixtures = [root / name for name in ("payload", "debug", "empty", "fixtures")]
        for directory in (payload, debug, empty, fixtures):
            directory.mkdir()
        expected = {"usr/sbin/hsflowd": 0o755,
                    **{"etc/hsflowd/modules/mod_" + name + ".so": 0o644 for name in MODULES},
                    "etc/hsflowd.conf": 0o644, "etc/init.d/hsflowd": 0o755,
                    "etc/dbus-1/system.d/net.sflow.hsflowd.conf": 0o644,
                    "usr/share/doc/hsflowd/copyright": 0o644,
                    "usr/share/doc/hsflowd/changelog.Debian.gz": 0o644}
        with tarfile.open(args.runtime) as archive:
            members = {m.name.removeprefix("./"): m for m in archive if not m.isdir()}
            assert set(members) == set(expected), set(members) ^ set(expected)
            for name, mode in expected.items():
                m = members[name]
                assert m.isfile() and (m.mode, m.uid, m.gid, m.mtime) == (mode, 0, 0, 1672560000), name
            archive.extractall(payload, filter="data")
        for source, destination in ((args.debug, debug), (args.hiredis, payload), (args.fixtures, fixtures)):
            with tarfile.open(source) as archive:
                archive.extractall(destination, filter="data")
        compressed = (payload / "usr/share/doc/hsflowd/changelog.Debian.gz").read_bytes()
        assert compressed[3:8] == b"\0" * 5, "gzip filename/timestamp must be absent"
        assert gzip.decompress(compressed) == args.changelog.read_bytes()
        metadata = json.loads(args.metadata.read_text())
        assert metadata["architecture"] == "amd64" and set(metadata["packages"]) == {"hsflowd"}
        fields = metadata["packages"]["hsflowd"]["control_fields"]
        assert fields["Version"] == "2.1.26-1" and "libhiredis" in fields["Depends"]
        build_ids = {}
        for relative, function in [("usr/sbin/hsflowd", "main")] + [
                ("etc/hsflowd/modules/mod_" + name + ".so", "mod_" + name) for name in MODULES]:
            binary = payload / relative
            elf = lambda *flags: run([args.readelf, *flags, binary], env)
            assert "Advanced Micro Devices X86-64" in elf("-h")
            assert not re.search(r"\((?:RPATH|RUNPATH)\)", elf("-d"))
            assert ".debug_info" not in elf("-SW")
            build_id = re.search(r"Build ID: ([0-9a-f]+)", elf("-n")).group(1)
            symbols = debug / "usr/lib/debug/.build-id" / build_id[:2] / (build_id[2:] + ".debug")
            assert symbols.is_file() and ".debug_info" in run([args.readelf, "-SW", symbols], env)
            assert build_id in run([args.readelf, "-n", symbols], env)
            section = root / "debuglink.bin"
            run([args.objcopy, "--dump-section", ".gnu_debuglink=" + str(section), binary, root / "inspection-copy"], env)
            link = section.read_bytes()
            assert link.split(b"\0", 1)[0].decode() == symbols.name
            assert struct.unpack("<I", link[-4:])[0] == zlib.crc32(symbols.read_bytes()) & 0xffffffff
            for directory, present in ((debug / "usr/lib/debug", True), (empty, False)):
                output = run(["gdb", "--nx", "--nh", "--batch", "-iex", "set auto-load off",
                    "-iex", "set debuginfod enabled off", "-ex", "set debug-file-directory " + str(directory),
                    "-ex", "file " + str(binary), "-ex", "info line " + function, "-ex", "ptype " + function], env)
                assert bool(re.search(r'Line \d+ of ".*\.c"', output)) == present, output
                if present:
                    assert "type =" in output
            build_ids[relative] = build_id
        evidence = {"status": "passed", "build_ids": build_ids,
                    "service": service_probe(root, payload, fixtures, env)}
        print(json.dumps(evidence, sort_keys=True))
        if os.environ.get("TEST_UNDECLARED_OUTPUTS_DIR"):
            (Path(os.environ["TEST_UNDECLARED_OUTPUTS_DIR"]) / "installed-hsflowd.json").write_text(json.dumps(evidence, indent=2) + "\n")


if __name__ == "__main__":
    main()
