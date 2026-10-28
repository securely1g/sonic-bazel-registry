"""Exercise the delivered libnl3 SDK and runtime in the native CI container.

Use the container's existing compiler for post-build consumer validation. The
Bazel producer, its declared tools and the published recipes stay unchanged.
"""

import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tarfile
import tempfile


STEMS = ("libnl-3", "libnl-genl-3", "libnl-route-3", "libnl-nf-3", "libnl-cli-3")
PLUGINS = {
    "cls/basic.so", "cls/cgroup.so", "qdisc/bfifo.so", "qdisc/blackhole.so",
    "qdisc/fq_codel.so", "qdisc/hfsc.so", "qdisc/htb.so", "qdisc/ingress.so",
    "qdisc/pfifo.so", "qdisc/plug.so",
}
SDK_CONSUMER = """
#define _GNU_SOURCE
#include <netlink/netlink.h>
#include <netlink/socket.h>
#include <netlink/route/link.h>
#include <netlink/route/pktloc.h>
int main(void) {
    struct nl_sock *socket = nl_socket_alloc();
    struct rtnl_link *link = rtnl_link_alloc();
    struct rtnl_pktloc *location = 0;
    if (!socket || !link || rtnl_pktloc_lookup("ip.src", &location) < 0) return 1;
    rtnl_pktloc_put(location);
    rtnl_link_put(link);
    nl_socket_free(socket);
    return 0;
}
"""


def checksum(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_loads(root):
    """Run in a new process so the loader sees the extracted library paths."""
    root = root.resolve()
    libraries = [root / (stem + ".so.200") for stem in STEMS]
    plugin_root = root / "libnl-3/cli"
    plugins = sorted(plugin_root.rglob("*.so"))
    assert {p.relative_to(plugin_root).as_posix() for p in plugins} == PLUGINS
    handles = [ctypes.CDLL(str(p), mode=os.RTLD_NOW | os.RTLD_LOCAL)
               for p in libraries + plugins]
    mapped = {Path(line.split()[-1]).resolve()
              for line in Path("/proc/self/maps").read_text().splitlines()
              if "/" in line.split()[-1]}
    expected = {p.resolve() for p in libraries + plugins}
    assert expected <= mapped, ("unmapped delivered ELF", expected - mapped)
    libnl = {p for p in mapped if p.name.startswith("libnl-") or "libnl-3/cli" in p.as_posix()}
    assert libnl == expected, ("unexpected libnl origin", libnl ^ expected)
    assert len(handles) == 15
    return [p.relative_to(root).as_posix() for p in sorted(expected)]


def check(artifacts):
    artifacts = artifacts.resolve()
    manifest = artifacts / "outputs.json"
    outputs = json.loads(manifest.read_text())
    records = {}
    for group in outputs.values():
        for record in group:
            previous = records.setdefault(record["path"], record)
            assert previous == record, ("conflicting output records", record["path"])
    environment = dict(os.environ, LC_ALL="C")
    environment.pop("LD_PRELOAD", None)
    environment.pop("LD_LIBRARY_PATH", None)
    environment.pop("LIBNL3_EXPECTED_LIBRARY_DIR", None)

    def run(command, env=environment):
        try:
            return subprocess.check_output([str(x) for x in command], text=True,
                                           stderr=subprocess.STDOUT, env=env, timeout=120)
        except subprocess.CalledProcessError as error:
            print(error.output, file=sys.stderr)
            raise

    triplet = run(["cc", "-print-multiarch"]).strip()
    architecture = {"x86_64-linux-gnu": "amd64", "aarch64-linux-gnu": "arm64"}[triplet]
    assert platform.machine() == {"amd64": "x86_64", "arm64": "aarch64"}[architecture]
    assert os.environ.get("CI_ARCHITECTURE", architecture) == architecture
    receipt = {"outputs_manifest_sha256": checksum(manifest), "architecture": architecture,
               "compiler": run(["cc", "--version"]).splitlines()[0],
               "archives": [], "consumers": []}

    def extract(filename, root):
        selected = [r for r in records.values() if Path(r["path"]).name == filename]
        assert len(selected) == 1, (filename, selected)
        record = selected[0]
        archive = (artifacts / record["path"]).resolve()
        assert archive.is_relative_to(artifacts / "outputs"), archive
        assert archive.stat().st_size == record["size"], archive
        assert checksum(archive) == record["sha256"], archive
        with tarfile.open(archive) as source:
            source.extractall(root, filter="data")
        receipt["archives"].append(record)

    with tempfile.TemporaryDirectory(prefix="libnl3-sdk-") as directory:
        work = Path(directory)
        root = work / "installed"
        root.mkdir()
        cpu = {"amd64": "x86_64", "arm64": "aarch64"}[architecture]
        for stem in STEMS:
            extract(stem + "_pkg_" + cpu + "_rttar.tar", root)
        extract("libnl-3-dev_files.tar", root)
        extract("libnl-route-3-dev_library_files_" + cpu + ".tar", root)
        libdir = root / "usr/lib" / triplet
        environment["NLSYSCONFDIR"] = str(root / "etc/libnl-3")
        shared_env = dict(environment, LD_LIBRARY_PATH=str(libdir),
                          LD_PRELOAD=":".join(str(libdir / (s + ".so.200")) for s in STEMS),
                          LIBNL3_EXPECTED_LIBRARY_DIR=str(libdir))
        source = work / "sdk_consumer.c"
        source.write_text(SDK_CONSUMER)
        # Exercise both the inherited installed SDK contract and SONiC's route
        # next-hop patch through extracted headers, archives and shared libraries.
        sources = [source, Path(__file__).resolve().parent.parent / "overlay/libnl3_consumer_test.c"]
        for index, source in enumerate(sources):
            common = ["cc", "-std=c11", "-Wall", "-Werror", "-I" + str(root / "usr/include/libnl3"), source]
            for mode in ("shared", "whole-archive"):
                binary = work / (str(index) + "-" + mode)
                if mode == "shared":
                    libraries = [libdir / "libnl-route-3.so", libdir / "libnl-3.so"]
                    assert all(p.is_file() and p.resolve().is_relative_to(libdir) for p in libraries)
                    flags = [*libraries, "-Wl,-rpath-link," + str(libdir), "-ldl"]
                else:
                    flags = ["-Wl,--whole-archive", libdir / "libnl-route-3.a", libdir / "libnl-3.a",
                             "-Wl,--no-whole-archive", "-lm", "-pthread", "-ldl"]
                run(common + flags + ["-o", binary])
                dynamic = run(["readelf", "-d", binary])
                if mode == "whole-archive":
                    assert not any("NEEDED" in line and "libnl" in line for line in dynamic.splitlines()), dynamic
                run([binary], shared_env if mode == "shared" else environment)
                receipt["consumers"].append({"source": source.name, "source_sha256": checksum(source),
                                             "mode": mode, "binary_sha256": checksum(binary)})
        receipt["loaded_elfs"] = json.loads(run([sys.executable, Path(__file__).resolve(),
                                                "--check-loads", libdir], shared_env))
    assert len(receipt["consumers"]) == 4 and len(receipt["loaded_elfs"]) == 15
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--artifacts", type=Path)
    mode.add_argument("--check-loads", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.check_loads:
        print(json.dumps(check_loads(args.check_loads)))
    else:
        result = check(args.artifacts)
        (args.artifacts / "libnl3-installed-sdk.json").write_text(json.dumps(result, indent=2) + "\n")
        print("Validated 4 extracted SDK consumers and loaded all 5 libraries and 10 plugins")
