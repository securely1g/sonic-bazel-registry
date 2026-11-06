#!/usr/bin/env python3
"""Use optional private Debian mirrors without publishing their locations."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mirror_privacy import PrivacyError, Redactor

SNAPSHOTS = (
    ("DEBIAN_MIRROR_BASE_URL", "debian", "20260727T143429Z"),
    ("DEBIAN_SECURITY_MIRROR_BASE_URL", "debian-security", "20260726T121236Z"),
)
# These undated binary-package URLs can try the same pinned private snapshots.
# A package absent from that snapshot still falls back to its original URL;
# its version, filename, and caller-supplied integrity remain unchanged.
BINARY_POOL_ORIGINS = (
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


def configuration(public: str, mirrors: dict[str, str], *, fallback: bool = True) -> str:
    """Prefer pinned private snapshots while retaining public package identity."""
    preferred, originals = [], []
    # Each segment starts with a non-dot, so traversal/hidden paths cannot match.
    segment = r"[A-Za-z0-9_+%:~-][A-Za-z0-9_+.%:~-]*"
    suffix = rf"((?:pool|dists)/(?:{segment}/)*{segment})"
    for key, archive, snapshot in SNAPSHOTS:
        if key not in mirrors:
            continue
        pattern = rf"(snapshot(?:-cloudflare)?\.debian\.org/archive/{archive}/{snapshot}/{suffix})"
        preferred.append(f"rewrite {pattern} {mirrors[key]}$2")
        originals.append(f"rewrite {pattern} https://$1")
    # CDN pool paths carry immutable package versions, unlike mutable dists/
    # indexes. Do not redirect indexes, source archives, other snapshot dates,
    # or arbitrary mirrors into one of the configured snapshots. Restrict URL
    # escapes to characters used in Debian filenames; encoded separators must
    # not escape the selected pool directory.
    component = r"(?:main|contrib|non-free|non-free-firmware)"
    directory = r"[A-Za-z0-9][A-Za-z0-9_+.-]*"
    filename = r"[A-Za-z0-9](?:[A-Za-z0-9_+.:~-]|%(?:2[bBdDeE]|3[aA]|5[fF]|7[eE]))*\.(?:deb|udeb)"
    for key, origin, pool in BINARY_POOL_ORIGINS:
        if key not in mirrors:
            continue
        suffix = rf"({pool}/{component}/{directory}/{directory}/{filename})"
        pattern = rf"({origin}/{suffix})"
        preferred.append(f"rewrite {pattern} {mirrors[key]}$2")
        # Bazel preserves the input protocol when no replacement scheme is
        # supplied, retaining both HTTPS and legacy HTTP originals exactly.
        originals.append(f"rewrite {pattern} $1")
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
            log: Path | None = None) -> int:
    """Capture inherited stderr too (including Bazel info/cquery diagnostics)."""
    output = log.open("w") if log else None
    try:
        with subprocess.Popen(command, cwd=cwd, env=child_environment(), stdin=subprocess.DEVNULL,
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
    if not mirrors:
        return execute(command, redactor)
    public = public_configuration(command, args.public_config).read_text()
    try:
        with private_directory(args.private_dir, artifacts) as temporary:
            config = Path(temporary) / "downloader.cfg"
            write_config(config, configuration(public, mirrors))
            receipt(artifacts, {"enabled": True, "archives": [archive for key, archive, _ in SNAPSHOTS
                                                               if key in mirrors],
                                "public_fallback": True, "package_integrity_unchanged": True})
            return execute([*command, DOWNLOADER_ARG + str(config)], redactor)
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
    for name in ("run", "probe", "check-artifacts"):
        command = sub.add_parser(name)
        command.add_argument("--artifacts", required=True, type=Path)
        if name != "check-artifacts":
            command.add_argument("--private-dir", required=True, type=Path)
            command.add_argument("--public-config", required=True, type=Path)
        if name == "run":
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
            redactor.scrub_and_scan(args.artifacts.resolve())
            return 0
        mirrors = selected_mirrors(dict(os.environ))
        return run(args, mirrors, redactor) if args.operation == "run" else probe(args, mirrors, redactor)
    except (OSError, ValueError, PrivacyError) as error:
        print(redactor.redact(f"Private mirror operation failed: {error}"), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
