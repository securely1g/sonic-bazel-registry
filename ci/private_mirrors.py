#!/usr/bin/env python3
"""Use optional private Debian mirrors without publishing their locations."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mirror_privacy import PrivacyError, Redactor
import debian_downloads
import http_audit

SNAPSHOTS = (
    ("DEBIAN_MIRROR_BASE_URL", "debian", "20260727T143429Z"),
    ("DEBIAN_SECURITY_MIRROR_BASE_URL", "debian-security", "20260726T121236Z"),
)
# Official CDN origins with separate binary snapshot and supplemental source routes.
CDN_POOL_ORIGINS = (
    ("DEBIAN_MIRROR_BASE_URL", r"deb\.debian\.org/debian", "pool"),
    ("DEBIAN_SECURITY_MIRROR_BASE_URL",
     r"(?:deb|security)\.debian\.org/debian-security", "pool/updates"),
)
DOWNLOADER_ARG = "--bazel-build-arg=--experimental_downloader_config="
PACKAGES = (
    ("DEBIAN_MIRROR_BASE_URL", "debian", "20260727T143429Z",
     "pool/main/a/audit/libaudit-dev_4.0.2-2+b2_amd64.deb",
     "4104cf1149947db1a3450b2a13aab23000a695aa6981f515216129ad8b884423"),
    ("DEBIAN_SECURITY_MIRROR_BASE_URL", "debian-security", "20260726T121236Z",
     "pool/updates/main/c/c-ares/libc-ares-dev_1.34.5-1+deb13u1_arm64.deb",
     "40d2336fb01e4b707ad8a6bfbad522fc7ddff3b057d16ee981237fb7cef5d95c"),
)


def selected_mirrors(environment: dict[str, str]) -> dict[str, str]:
    mirrors = {}
    for key, archive, snapshot in SNAPSHOTS:
        value = environment.get(key, "")
        if not value:
            continue
        try:
            parsed = urlsplit(value)
            port = parsed.port
            valid = (parsed.scheme == "https" and parsed.hostname and
                     re.fullmatch(r"[A-Za-z0-9.-]+", parsed.hostname) and
                     (port is None or 1 <= port <= 65535) and
                     not parsed.username and not parsed.password and
                     not parsed.query and not parsed.fragment and
                     parsed.path.rstrip("/").endswith(f"/archive/{archive}/{snapshot}") and
                     re.fullmatch(r"/[A-Za-z0-9_./-]+", parsed.path) and
                     ".." not in parsed.path.split("/") and
                     not any(c.isspace() for c in value))
        except ValueError:
            valid = False
        if not valid:
            raise ValueError(f"Invalid HTTPS snapshot base in {key}")
        mirrors[key] = value.rstrip("/") + "/"
    return mirrors


# Suffixes present in these immutable signed Debian Release manifests. APT's
# resolver also probes other encodings in parallel. A public retry for an
# unpublished encoding cannot recover a valid signed index.
INDEX_FORMATS = {
    ("debian", "20260727T143429Z"): {
        "bookworm": ("", ".gz", ".xz"), "bookworm-updates": ("", ".xz"),
        "trixie": ("", ".gz", ".xz"), "trixie-updates": ("", ".xz"),
    },
    ("debian-security", "20260726T121236Z"): {
        "bookworm-security": ("", ".xz"), "trixie-security": ("", ".xz"),
    },
}


def unpublished_index_pattern(archive: str, snapshot: str) -> str:
    paths = []
    arch = r"(?:amd64|arm64|armhf)"
    for suite, packages in INDEX_FORMATS.get((archive, snapshot), {}).items():
        for index, published in ((f"binary-{arch}/Packages", packages), (f"Contents-{arch}", ("", ".gz"))):
            missing = [re.escape(ext) for ext in (".gz", ".xz", ".bz2") if ext not in published]
            paths.append(rf"dists/{suite}/main/{index}(?:{'|'.join(missing)})")
    return rf"(?!{snapshot}/(?:{'|'.join(paths)})$)" if paths else ""


def configuration(public: str, mirrors: dict[str, str], *, fallback: bool = True) -> str:
    """Prefer pinned private snapshots while retaining public package identity."""
    preferred, originals = [], []
    # Each segment starts with a non-dot, so traversal/hidden paths cannot match.
    first = r"(?:[A-Za-z0-9_+:~-]|%(?:2[bBdD]|3[aA]|5[fF]|7[eE]))"
    rest = r"(?:[A-Za-z0-9_+.:~-]|%(?:2[bBdDeE]|3[aA]|5[fF]|7[eE]))*"
    segment = first + rest
    suffix = rf"((?:pool|dists)/(?:{segment}/)*{segment})"
    for key, archive, snapshot in SNAPSHOTS:
        if key not in mirrors:
            continue
        # Keep the requested date. Historical inputs such as BusyBox and
        # Socat have their own paths under the same private archive.
        dated_root = mirrors[key].removesuffix(snapshot + "/")
        stamp = r"([0-9]{8}T[0-9]{6}Z)"
        origin = rf"snapshot(?:-cloudflare)?\.debian\.org/archive/{archive}/"
        pattern = rf"({origin}{stamp}/{suffix})"
        preferred.append(f"rewrite {pattern} {dated_root}$2/$3")
        eligible = unpublished_index_pattern(archive, snapshot)
        originals.append(f"rewrite ({origin}{eligible}{stamp}/{suffix}) https://$1")
    # Keep undated binary packages on the configured snapshot. Debian CDN
    # source archives have no snapshot identity; the mirror serves their
    # checked, versioned bytes at the original CDN pool path.
    component = r"(?:main|contrib|non-free|non-free-firmware)"
    directory = r"[A-Za-z0-9][A-Za-z0-9_+.-]*"
    package_name = r"[A-Za-z0-9]" + rest
    snapshot_roots = {key: (archive, snapshot) for key, archive, snapshot in SNAPSHOTS}
    for key, origin, pool in CDN_POOL_ORIGINS:
        if key not in mirrors:
            continue
        archive, snapshot = snapshot_roots[key]
        mirror = mirrors[key]
        source_pool = mirror.removesuffix(f"archive/{archive}/{snapshot}/") + archive + "/"
        for extensions, base in ((r"deb|udeb", mirror),
                                 (r"dsc|diff\.gz|tar\.(?:gz|bz2|xz|lzma|zst)", source_pool)):
            suffix = rf"({pool}/{component}/{directory}/{directory}/{package_name}\.(?:{extensions}))"
            pattern = rf"({origin}/{suffix})"
            preferred.append(f"rewrite {pattern} {base}$2")
            # A scheme-less replacement preserves the original HTTP/HTTPS.
            originals.append(f"rewrite {pattern} $1")
    # snapshot.debian.org/file/ uses the SHA1 as an object locator. The
    # caller's independent archive integrity is still checked by Bazel.
    content_pattern = r"(snapshot(?:-cloudflare)?\.debian\.org/(file/[0-9a-fA-F]{40}))"
    origins = dict.fromkeys(mirrors[key].removesuffix(f"archive/{archive}/{snapshot}/")
                            for key, archive, snapshot in SNAPSHOTS if key in mirrors)
    for origin in origins:
        preferred.append(f"rewrite {content_pattern} {origin}$2")
    if origins:
        originals.append(f"rewrite {content_pattern} https://$1")
    if not fallback:
        return "\n".join(preferred) + "\n"
    return "\n".join(preferred) + "\n" + public.rstrip() + "\n" + "\n".join(originals) + "\n"


def public_configuration(command: list[str], default: Path) -> Path:
    """Honor a caller's final public downloader selection before adding mirrors."""
    selected = default
    for flag in command:
        if flag.startswith(DOWNLOADER_ARG):
            selected = Path(flag[len(DOWNLOADER_ARG):])
    return selected


def child_environment() -> dict[str, str]:
    environment = dict(os.environ)
    for key, _, _ in SNAPSHOTS:
        environment.pop(key, None)
    return environment


def execute(command: list[str], redactor: Redactor, *, cwd: Path | None = None,
            log: Path | None = None, extra_environment: dict[str, str] | None = None) -> int:
    """Capture inherited stderr too (including Bazel info/cquery diagnostics)."""
    output = log.open("w") if log else None
    try:
        with subprocess.Popen(command, cwd=cwd, env=child_environment() | (extra_environment or {}), stdin=subprocess.DEVNULL,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True, errors="replace") as process:
            assert process.stdout is not None
            for line in process.stdout:
                safe = redactor.redact(line)
                print(safe, end="", flush=True)
                if output:
                    output.write(safe)
            return process.wait()
    finally:
        if output:
            output.close()


def private_directory(parent: Path, artifacts: Path):
    parent = parent.resolve()
    if parent == artifacts or parent.is_relative_to(artifacts):
        raise ValueError("Private mirror configuration must be outside artifacts")
    parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    return tempfile.TemporaryDirectory(prefix="mirror-", dir=parent)


def write_config(path: Path, content: str) -> None:
    with open(path, "x", opener=lambda p, flags: os.open(p, flags, 0o600)) as stream:
        stream.write(content)


def receipt(artifacts: Path, value: dict) -> None:
    artifacts.mkdir(parents=True, exist_ok=True)
    (artifacts / "private-mirrors.json").write_text(json.dumps(value, indent=2) + "\n")


def run(args, mirrors: dict[str, str], redactor: Redactor) -> int:
    command = args.child[1:] if args.child[:1] == ["--"] else args.child
    if not command:
        raise ValueError("Missing registry validation command")
    artifacts = args.artifacts.resolve()
    suite = getattr(args, "operation", "run") == "suite"
    log = None
    if suite:
        artifacts.mkdir(parents=True, exist_ok=True)
        log = artifacts / "runner-tests.log"
    if not mirrors:
        return execute(command, redactor, log=log)
    public = public_configuration(command, args.public_config).read_text()
    try:
        with private_directory(args.private_dir, artifacts) as temporary:
            config = Path(temporary) / "downloader.cfg"
            write_config(config, configuration(public, mirrors))
            # APT and nested Bazel invocations cannot use the parent process's
            # environment secrets. Keep their configuration in this private
            # directory and retain transfer evidence from preparation commands.
            apt_map = Path(temporary) / "apt-mirrors.json"
            bases = {f"https://snapshot.debian.org/archive/{archive}/{stamp}": mirrors[key]
                     for key, archive, stamp in SNAPSHOTS if key in mirrors}
            write_config(apt_map, json.dumps({"schema_version": 1, "mirrors": bases}))
            environment = {"SONIC_APT_MIRROR_CONFIG": str(apt_map)}
            command = list(command)
            real_bazel = os.environ.get("REGISTRY_CI_TEST_BAZEL") if suite else None
            bazel_index = None
            if not suite and "--bazel" in command:
                bazel_index = command.index("--bazel") + 1
                real_bazel = command[bazel_index]
            receipt(artifacts, {"enabled": True, "archives": [archive for key, archive, _ in SNAPSHOTS
                                                               if key in mirrors],
                                "public_fallback": True, "package_integrity_unchanged": True,
                                "http_observer_expected": bool(real_bazel)})
            if real_bazel:
                if getattr(args, "http_audit_jar", None):
                    try:
                        http_audit.prepare(Path(temporary), args.http_audit_jar, mirrors)
                    except (OSError, ValueError) as error:
                        print(redactor.redact(f"::warning::Debian HTTP observer unavailable: {error}"))
                launcher = Path(temporary) / "bazel"
                trace = [sys.executable, str(Path(debian_downloads.__file__).resolve()), real_bazel,
                         str(artifacts), temporary, str(apt_map)]
                launcher.write_text("#!/bin/sh\nexec " + shlex.join(trace) + ' "$@"\n')
                launcher.chmod(0o700)
                if bazel_index is None:
                    # The sealed observer regression installs its own agent and
                    # uses loopback servers to exercise intentional public paths.
                    environment["REGISTRY_CI_HTTP_AUDIT_FIXTURE_BAZEL"] = real_bazel
                    if getattr(args, "http_audit_jar", None):
                        environment["REGISTRY_CI_HTTP_AUDIT_FIXTURE_JAR"] = str(Path(temporary) / "http-audit.jar")
                    environment["REGISTRY_CI_TEST_BAZEL"] = str(launcher)
                else:
                    command[bazel_index] = str(launcher)
            if not suite:
                command.append(DOWNLOADER_ARG + str(config))
            try:
                return execute(command, redactor, log=log, extra_environment=environment)
            finally:
                http_audit.retain(Path(temporary), artifacts)
    finally:
        redactor.scrub_and_scan(artifacts)


def probe(args, mirrors: dict[str, str], redactor: Redactor) -> int:
    artifacts = args.artifacts.resolve()
    if len(mirrors) != len(SNAPSHOTS):
        raise ValueError("Both snapshot secrets are required for the explicit private mirror probe")
    artifacts.mkdir(parents=True, exist_ok=True)
    try:
        with private_directory(args.private_dir, artifacts) as temporary:
            work = Path(temporary)
            config = work / "downloader.cfg"
            # No public fallback in this proof: success must come from the mirror.
            write_config(config, configuration("", mirrors, fallback=False))
            declarations = ['module(name = "private_mirror_probe")',
                            'http_file = use_repo_rule("@bazel_tools//tools/build_defs/repo:http.bzl", "http_file")']
            checked = []
            for key, archive, snapshot, suffix, checksum in PACKAGES:
                if key not in mirrors:
                    continue
                name = archive.replace("-", "_") + "_probe"
                original = f"https://snapshot.debian.org/archive/{archive}/{snapshot}/{suffix}"
                declarations.append(f'http_file(name={name!r}, urls=[{original!r}], sha256={checksum!r})')
                checked.append({"repository": name, "archive": archive, "original_url": original,
                                "sha256": checksum})
            (work / "MODULE.bazel").write_text("\n".join(declarations) + "\n")
            (work / "BUILD.bazel").write_text("")
            cache = work / "repository-cache"
            cache.mkdir()
            for package in checked:
                command = [args.bazel, "--batch", "--ignore_all_rc_files",
                           f"--output_user_root={work / 'bazel'}", "fetch",
                           f"--repo=@{package['repository']}", "--registry=https://bcr.bazel.build/",
                           f"--repository_cache={cache}", "--lockfile_mode=update",
                           f"--build_event_json_file={artifacts / (package['repository'] + '-events.jsonl')}",
                           f"--experimental_downloader_config={config}",
                           "--http_connector_attempts=2", "--http_connector_retry_max_timeout=5s"]
                result = execute(command, redactor, cwd=work,
                                 log=artifacts / (package["repository"] + ".log"))
                if result:
                    raise ValueError("Private mirror Bazel download proof failed")
                fetched = cache / "content_addressable" / "sha256" / package["sha256"] / "file"
                with fetched.open("rb") as stream:
                    if hashlib.file_digest(stream, "sha256").hexdigest() != package["sha256"]:
                        raise ValueError("Private mirror package checksum mismatch")
            receipt(artifacts, {"enabled": True, "probe": "passed", "fresh_repository_cache": True,
                                "public_fallback_in_probe": False, "packages": checked})
        return 0
    finally:
        redactor.scrub_and_scan(artifacts)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="operation", required=True)
    for name in ("run", "suite", "probe", "check-artifacts"):
        command = sub.add_parser(name)
        command.add_argument("--artifacts", required=True, type=Path)
        if name != "check-artifacts":
            command.add_argument("--private-dir", required=True, type=Path)
            command.add_argument("--public-config", required=True, type=Path)
        if name in ("run", "suite"):
            command.add_argument("--http-audit-jar", type=Path)
            command.add_argument("child", nargs=argparse.REMAINDER)
        if name == "probe":
            command.add_argument("--bazel", default="bazel")
    args = parser.parse_args()
    try:
        redactor = Redactor([os.environ[key] for key, _, _ in SNAPSHOTS if os.environ.get(key)])
        redactor.mask_github()
    except Exception:
        print("Could not initialize private mirror protection", file=sys.stderr)
        return 1
    try:
        if args.operation == "check-artifacts":
            artifacts = args.artifacts.resolve()
            redactor.scrub_and_scan(artifacts)
            if redactor.patterns and artifacts.is_dir():
                report = debian_downloads.report(artifacts)
                data = json.dumps(report, indent=2) + "\n"
                redactor.write_checked_text(artifacts / "debian-downloads.json", data)
                if report["incomplete_traces"] or not report["inputs"]:
                    print("::warning::Debian download evidence is incomplete; see debian-downloads.json")
                if report["http_observer"]["public_requests"]:
                    print("::warning::Bazel made public Debian HTTP requests; see debian-downloads.json")
                if report["exceptions"]:
                    print(f"::warning::{len(report['exceptions'])} public or unattributed Debian "
                          "download records; see debian-downloads.json")
            return 0
        mirrors = selected_mirrors(dict(os.environ))
        return run(args, mirrors, redactor) if args.operation in ("run", "suite") else probe(args, mirrors, redactor)
    except (OSError, ValueError, PrivacyError) as error:
        print(redactor.redact(f"Private mirror operation failed: {error}"), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
