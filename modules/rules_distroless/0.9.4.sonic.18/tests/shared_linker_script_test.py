"""Compile a sandboxed shared library against a cross-package Debian linker script.

Contract: a public APT CcInfo must carry the inputs required by its linker script
through cc_shared_library, and the resulting library must return the known value.
No production package index or business component is used.
"""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, required=True)
    args = parser.parse_args()
    root = Path(tempfile.mkdtemp(prefix="apt-shared-script-"))
    print("Evidence:", root, flush=True)
    architecture = subprocess.check_output(["dpkg", "--print-architecture"], text=True).strip()
    (root / "runtime.c").write_text("int fixture_answer(void) { return 42; }\n")
    library = root / "libfixture.so.1"
    subprocess.run(["gcc", "-shared", "-fPIC", "-Wl,-soname,libfixture.so.1", str(root / "runtime.c"), "-o", str(library)], check=True)
    packages = {}
    for name, files, depends in [
        ("libfixture1", {"usr/lib/libfixture.so.1": library.read_bytes()}, []),
        ("libfixture-dev", {
            "usr/lib/libfixture.so": b"GROUP ( /usr/lib/libfixture.so.1 )\n",
            "usr/include/fixture.h": b"int fixture_answer(void);\n",
            "usr/lib/pkgconfig/fixture.pc": b"prefix=/usr\nlibdir=${prefix}/lib\nincludedir=${prefix}/include\nName: fixture\nDescription: shared script fixture\nVersion: 1\nLibs: -L${libdir} -lfixture\nCflags: -I${includedir}\n",
        }, ["libfixture1"]),
    ]:
        tree = root / name
        (tree / "DEBIAN").mkdir(parents=True)
        (tree / "DEBIAN/control").write_text(f"Package: {name}\nVersion: 1\nArchitecture: {architecture}\nMaintainer: Fixture <fixture@example.invalid>\nDescription: shared linker script contract\n")
        for path, data in files.items():
            output = tree / path
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(data)
        archive = root / (name + ".deb")
        subprocess.run(["dpkg-deb", "--root-owner-group", "-Zxz", "--build", str(tree), str(archive)], check=True, capture_output=True)
        packages[f"/fixture/{name}:{architecture}=1"] = {
            "name": name, "version": "1", "suite": "fixture", "architecture": architecture,
            "filename": archive.name, "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
            "files": sorted(files), "depends_on": [f"/fixture/{dep}:{architecture}=1" for dep in depends],
        }
    lock = {"version": 2, "sources": {"fixture": {"uris": [root.as_uri()]}}, "packages": packages,
            "dependency_sets": {"locked": {"sets": {architecture: {f"/fixture/libfixture-dev:{architecture}": "1"}}}}}
    (root / "apt.lock.json").write_text(json.dumps(lock))
    (root / "MODULE.bazel").write_text('''module(name="shared_linker_script_contract")
bazel_dep(name="rules_distroless",version="0.9.4.sonic.18")
bazel_dep(name="rules_cc",version="0.2.20")
apt=use_extension("@rules_distroless//apt:extensions.bzl","apt")
apt.import_lock(lock="//:apt.lock.json",libraries=True)
use_repo(apt,"locked")
''')
    (root / "middle.c").write_text('#include <fixture.h>\nint fixture_sum(void) { return fixture_answer() + 1; }\n')
    (root / "BUILD.bazel").write_text('''load("@rules_cc//cc:defs.bzl","cc_library","cc_shared_library")
exports_files(["apt.lock.json"])
cc_library(name="middle",srcs=["middle.c"],deps=["@locked//libfixture-dev:libfixture"])
cc_shared_library(name="combined",deps=[":middle"],user_link_flags=["-Wl,-z,defs"])
''')
    bazel = ["bazel", "--nohome_rc", "--nosystem_rc", "--max_idle_secs=60"]
    options = ["--registry=" + args.registry.resolve().as_uri(), "--registry=https://bcr.bazel.build", "--spawn_strategy=sandboxed", "--sandbox_base=" + str(root / "sandbox")]
    (root / "sandbox").mkdir()
    env = dict(os.environ, USE_BAZEL_VERSION="8.5.1")
    with (root / "build.log").open("w") as log:
        result = subprocess.run(bazel + ["build"] + options + ["//:combined"], cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT)
    if result.returncode:
        raise SystemExit("Shared library build failed; see " + str(root / "build.log"))
    result = subprocess.run(bazel + ["cquery"] + options + ["//:combined", "--output=files"], cwd=root, env=env, capture_output=True, text=True, check=True)
    combined = next(root / path for path in result.stdout.splitlines() if path.endswith(".so"))
    dynamic = subprocess.check_output(["readelf", "-d", str(combined)], text=True)
    assert "[libfixture.so.1]" in dynamic, dynamic
    # Preload the known SONAME so this assertion tests the linked result without
    # depending on a host installation of the synthetic runtime library.
    ctypes.CDLL(str(library), mode=ctypes.RTLD_GLOBAL)
    shared = ctypes.CDLL(str(combined))
    assert shared.fixture_sum() == 43
    print("PASS: sandboxed cross-package linker script and shared library returned 43", flush=True)


if __name__ == "__main__":
    main()
