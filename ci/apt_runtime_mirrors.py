#!/usr/bin/env python3
"""Prepare a verified owner's missing test runtimes through standard APT mirrors.

This CI adapter leaves the owner's source and normal validation invocation intact.
Its preparation protocol consists of the existing selection, provenance, inventory,
and verification functions used by Common's pinned runtime preparer. APT remains
responsible for signature verification, dependency planning, download, and install.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import runpy
import subprocess
import tempfile
from urllib.parse import urlsplit


PROTOCOL = ("select_runtime", "snapshot_sources", "inventory", "missing_packages", "verify_inventory")
SNAPSHOT = re.compile(r"https://snapshot\.debian\.org/archive/(?:debian|debian-security)/[0-9]{8}T[0-9]{6}Z")


def load_owner(script: Path, expected_sha256: str) -> dict:
    if hashlib.sha256(script.read_bytes()).hexdigest() != expected_sha256:
        raise ValueError("Test runtime preparation script checksum mismatch")
    owner = runpy.run_path(str(script))
    if any(not callable(owner.get(name)) for name in PROTOCOL):
        raise ValueError("Verified runtime helper does not implement the APT preparation protocol")
    return owner


def read_mirrors(path: Path) -> dict[str, str]:
    config = json.loads(path.read_text())
    if (set(config) != {"schema_version", "mirrors"} or config["schema_version"] != 1
            or not isinstance(config["mirrors"], dict)):
        raise ValueError("Invalid APT mirror configuration schema")
    mirrors = {}
    for source, mirror in config["mirrors"].items():
        if not isinstance(source, str) or not SNAPSHOT.fullmatch(source):
            raise ValueError("APT mirrors must identify a canonical Debian snapshot base")
        if not isinstance(mirror, str) or any(c.isspace() or ord(c) < 32 for c in mirror):
            raise ValueError("Invalid APT mirror URL")
        parsed = urlsplit(mirror)
        if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
                or parsed.query or parsed.fragment):
            raise ValueError("APT mirrors require HTTPS base URLs without credentials, query, or fragment")
        mirrors[source] = mirror.rstrip("/")
    return mirrors


def snapshot_base(url: str) -> str:
    base, separator, _ = url.partition("/pool/")
    if not separator or not SNAPSHOT.fullmatch(base):
        raise ValueError("Runtime inputs must come from canonical Debian snapshots")
    return base


def write_sources(root: Path, selected: dict, architecture: str, mirrors: dict[str, str]) -> dict:
    """Write priority-ordered APT mirror lists; never persist private URLs in receipts."""
    sources = set()
    mapped, unmapped = set(), set()
    for package in selected.values():
        source = snapshot_base(package["urls"][0])
        suite = package["suite"]
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", suite):
            raise ValueError("Invalid selected Debian suite")
        if source in mirrors:
            name = hashlib.sha256(source.encode()).hexdigest() + ".mirrors"
            mirror_file = root / name
            if not mirror_file.exists():
                descriptor = os.open(mirror_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(descriptor, "w") as stream:
                    stream.write(f"{mirrors[source]}/\tpriority:1\n{source}/\tpriority:2\n")
                    stream.flush()
                    os.fchmod(stream.fileno(), 0o400)
                    if os.geteuid() == 0:
                        # Only APT's sandboxed downloader and privileged root can
                        # read private endpoints. Do not disable APT's sandbox.
                        os.fchown(stream.fileno(), pwd.getpwnam("_apt").pw_uid, -1)
            transport = "mirror+" + mirror_file.as_uri()
            mapped.add(source)
        else:
            transport = source
            unmapped.add(source)
        sources.add(f"deb [arch={architecture} check-valid-until=no] {transport} {suite} main")
    (root / "sources.list").write_text("\n".join(sorted(sources)) + "\n")
    return {"mapped_snapshots": sorted(mapped), "unmapped_snapshots": sorted(unmapped)}


def verify_archives(archives: Path, selected: dict, requested: list[str]) -> list[dict]:
    expected = set(requested)
    verified = {}
    for archive in sorted(archives.glob("*.deb")):
        fields = subprocess.check_output([
            "dpkg-deb", "-f", str(archive), "Package", "Version", "Architecture",
        ], text=True)
        metadata = dict(line.split(": ", 1) for line in fields.splitlines())
        name, version, architecture = (metadata[key] for key in ("Package", "Version", "Architecture"))
        package = selected.get(name)
        with archive.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        identity = f"{name}:{architecture}={version}"
        if (not package or version != package["version"] or architecture != package["architecture"]
                or digest != package["sha256"] or identity not in expected or identity in verified):
            raise ValueError(f"APT downloaded an unselected runtime package: {archive.name}")
        verified[identity] = {"package": name, "version": version, "architecture": architecture, "sha256": digest}
    if set(verified) != expected:
        raise ValueError("APT did not download the complete selected missing runtime set")
    return [verified[key] for key in sorted(verified)]


def prepare(owner: dict, lock: Path, mirror_config: Path, log_path: Path, output: Path,
            architecture: str) -> dict:
    if architecture not in ("amd64", "arm64"):
        raise ValueError("Only native AMD64 and ARM64 test containers are supported")
    selected = owner["select_runtime"](json.loads(lock.read_text()), architecture)
    # Reuse the owner's original provenance check even for preinstalled packages.
    owner["snapshot_sources"](selected, architecture)
    mirrors = read_mirrors(mirror_config)
    before = owner["inventory"]()
    requested = owner["missing_packages"](selected, before)
    receipt = {"schema_version": 1, "architecture": architecture,
               "lock_sha256": hashlib.sha256(lock.read_bytes()).hexdigest(),
               "requested_packages": requested, "verified_downloads": [],
               "apt_log": log_path.name, "result": "incomplete"}
    log_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with log_path.open("w") as log:
            if requested:
                with tempfile.TemporaryDirectory(prefix="sonic-apt-runtime-") as temporary:
                    root = Path(temporary)
                    root.chmod(0o711)
                    receipt.update(write_sources(root, selected, architecture, mirrors))
                    (root / "preferences").touch()
                    for directory in ("lists/partial", "archives/partial", "sources.list.d", "preferences.d"):
                        (root / directory).mkdir(parents=True)
                    apt = ["apt-get", "-o", f"Dir::Etc::sourcelist={root / 'sources.list'}",
                           "-o", f"Dir::Etc::sourceparts={root / 'sources.list.d'}",
                           "-o", f"Dir::Etc::preferences={root / 'preferences'}",
                           "-o", f"Dir::Etc::preferencesparts={root / 'preferences.d'}",
                           "-o", f"Dir::State::lists={root / 'lists'}",
                           "-o", f"Dir::Cache::archives={root / 'archives'}",
                           "-o", "Acquire::Check-Valid-Until=false"]
                    environment = dict(os.environ, DEBIAN_FRONTEND="noninteractive")

                    def run(arguments: list[str]) -> None:
                        subprocess.run([*apt, *arguments], env=environment, stdout=log,
                                       stderr=subprocess.STDOUT, check=True)

                    run(["update"])
                    arguments = ["--yes", "--no-remove", "--no-install-recommends", "install", *requested]
                    plan = subprocess.check_output([*apt, "--simulate", *arguments], env=environment, text=True)
                    log.write(plan)
                    log.flush()
                    if any(line.startswith("Remv ") or re.match(r"Inst \S+ \[", line)
                           for line in plan.splitlines()):
                        raise ValueError("Runtime setup must not remove or change prepared-base packages")
                    run(["--download-only", *arguments])
                    receipt["verified_downloads"] = verify_archives(root / "archives", selected, requested)
                    run(["--no-download", *arguments])
                subprocess.run(["ldconfig"], check=True)
            else:
                log.write("No missing runtime packages; no APT invocation was needed.\n")
        after = owner["inventory"]()
        owner["verify_inventory"](selected, before, after)
        if owner["missing_packages"](selected, after):
            raise ValueError("Owner runtime validation would still need package downloads")
        receipt["preserved_base_packages"] = before
        receipt["installed_packages"] = after
        receipt["result"] = "passed"
        return receipt
    finally:
        output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner-script", type=Path, required=True)
    parser.add_argument("--owner-sha256", required=True)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--mirror-config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if os.geteuid() != 0 or not any(Path(p).exists() for p in ("/.dockerenv", "/run/.containerenv")):
        raise RuntimeError("APT runtime preparation requires root inside a disposable test container")
    if "VERSION_CODENAME=trixie" not in Path("/etc/os-release").read_text().splitlines():
        raise RuntimeError("APT runtime preparation requires Debian Trixie")
    owner = load_owner(args.owner_script, args.owner_sha256)
    architecture = subprocess.check_output(["dpkg", "--print-architecture"], text=True).strip()
    prepare(owner, args.lock, args.mirror_config, args.output.with_suffix(".apt.log"), args.output, architecture)
    print("Prepared missing locked test runtimes through APT mirror sources")


if __name__ == "__main__":
    main()
