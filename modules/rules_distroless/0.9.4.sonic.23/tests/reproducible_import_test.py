"""Keep unified APT lock imports out of the workspace MODULE.bazel.lock.

Contract: a unified apt.import_lock reads only tracked files, so it is marked
reproducible. Bazel must keep its repository specifications out of the
workspace lockfile, cache them in the output base, still build the imported
payloads, and accept the resulting lockfile in error mode. A legacy per-lock
import keeps its existing lockfile entry. No production package index is used.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile

EXTENSION = "@@rules_distroless+//apt:extensions.bzl%apt"
VERSION = "0.9.4.sonic.23"


def fixture_lock(root, architecture):
    """Build one synthetic DEB and a version-2 lock that references it."""
    tree = root / "fixture-data"
    (tree / "DEBIAN").mkdir(parents=True)
    (tree / "DEBIAN/control").write_text(
        f"Package: fixture-data\nVersion: 1\nArchitecture: {architecture}\n"
        "Maintainer: Fixture <fixture@example.invalid>\nDescription: reproducible import contract\n")
    (tree / "usr/share/fixture").mkdir(parents=True)
    (tree / "usr/share/fixture/answer.txt").write_text("42\n")
    archive = root / "fixture-data.deb"
    subprocess.run(["dpkg-deb", "--root-owner-group", "-Zxz", "--build", str(tree), str(archive)],
                   check=True, capture_output=True)
    key = f"/fixture/fixture-data:{architecture}=1"
    return {
        "version": 2,
        "sources": {"fixture": {"uris": [root.as_uri()]}},
        "packages": {key: {
            "name": "fixture-data", "version": "1", "suite": "fixture", "architecture": architecture,
            "filename": archive.name, "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
            "files": ["usr/share/fixture/answer.txt"], "depends_on": [],
        }},
        "dependency_sets": {"locked": {"sets": {architecture: {f"/fixture/fixture-data:{architecture}": "1"}}}},
    }


def consumer(root, name, lock, import_arguments):
    workspace = root / name
    workspace.mkdir()
    (workspace / "apt.lock.json").write_text(json.dumps(lock))
    (workspace / "BUILD.bazel").write_text('exports_files(["apt.lock.json"])\n')
    (workspace / "MODULE.bazel").write_text(f'''module(name = "reproducible_import_{name}")

bazel_dep(name = "rules_distroless", version = "{VERSION}")

apt = use_extension("@rules_distroless//apt:extensions.bzl", "apt")
apt.import_lock({import_arguments})
use_repo(apt, "locked")
''')
    return workspace


def bazel(root, workspace, registry, command, *arguments, log):
    startup = ["bazel", "--nohome_rc", "--nosystem_rc", "--max_idle_secs=60",
               "--output_base=" + str(root / (workspace.name + "-output"))]
    options = ["--registry=" + registry.resolve().as_uri(), "--registry=https://bcr.bazel.build"]
    env = dict(os.environ, USE_BAZEL_VERSION="8.5.1")
    with (root / log).open("w") as output:
        result = subprocess.run(startup + [command] + options + list(arguments), cwd=workspace, env=env,
                                stdout=output, stderr=subprocess.STDOUT)
    if result.returncode:
        raise SystemExit(f"bazel {command} failed in {workspace.name}; see {root / log}")


def extension_specs(path):
    document = json.loads(path.read_text())
    entry = document.get("moduleExtensions", {}).get(EXTENSION)
    return None if entry is None else entry["general"]["generatedRepoSpecs"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, required=True)
    args = parser.parse_args()
    root = Path(tempfile.mkdtemp(prefix="apt-reproducible-import-"))
    print("Evidence:", root, flush=True)
    architecture = subprocess.check_output(["dpkg", "--print-architecture"], text=True).strip()
    lock = fixture_lock(root, architecture)

    # Unified import: libraries = True selects the reviewed production-lock path.
    unified = consumer(root, "unified", lock, 'lock = "//:apt.lock.json", libraries = True')
    bazel(root, unified, args.registry, "build", "--lockfile_mode=update", "@locked//fixture-data:data",
          log="unified-build.log")
    workspace_lock = unified / "MODULE.bazel.lock"
    assert workspace_lock.is_file(), "Bazel did not write the workspace MODULE.bazel.lock"
    assert extension_specs(workspace_lock) is None, "unified APT import is still recorded in MODULE.bazel.lock"
    cached = extension_specs(root / "unified-output" / "MODULE.bazel.lock")
    assert cached and any(name.endswith("fixture-data-" + architecture + "_1") for name in cached), \
        "the output-base lockfile does not cache the imported package repository"
    bazel(root, unified, args.registry, "cquery", "--lockfile_mode=update", "@locked//fixture-data:data",
          "--output=files", log="unified-files.log")
    outputs = [line for line in (root / "unified-files.log").read_text().splitlines() if ".tar" in line]
    assert outputs, "the imported data target produced no archive"
    with tarfile.open(unified / outputs[0]) as payload:
        names = [member.name for member in payload.getmembers()]
    assert any(name.endswith("usr/share/fixture/answer.txt") for name in names), names
    # A committed lockfile without the APT entry must satisfy error mode.
    bazel(root, unified, args.registry, "build", "--lockfile_mode=error", "@locked//fixture-data:data",
          log="unified-error-mode.log")

    # Legacy per-lock import keeps its existing, non-reproducible lockfile entry.
    legacy = consumer(root, "legacy", lock, 'lock = "//:apt.lock.json", dependency_sets = ["locked"]')
    bazel(root, legacy, args.registry, "build", "--lockfile_mode=update", "@locked//fixture-data:data",
          log="legacy-build.log")
    assert extension_specs(legacy / "MODULE.bazel.lock"), "legacy APT import lost its lockfile entry"

    for workspace in (unified, legacy):
        subprocess.run(["bazel", "--output_base=" + str(root / (workspace.name + "-output")), "shutdown"],
                       cwd=workspace, env=dict(os.environ, USE_BAZEL_VERSION="8.5.1"), capture_output=True)
    print(f"PASS: unified import kept out of MODULE.bazel.lock ({workspace_lock.stat().st_size} bytes) "
          f"with {len(cached)} cached repositories; error mode accepted it; legacy import still recorded",
          flush=True)


if __name__ == "__main__":
    main()
