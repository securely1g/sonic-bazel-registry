#!/usr/bin/env python3
"""Verify manifest-selected GitHub assets and supply Bazel's standard distdir.

This helper fetches only explicit GitHub locations. It is not a network policy
for the Bazel process, and never executes files or extracts archive paths.
"""

from __future__ import annotations

import argparse
import hashlib
from http.client import HTTPException
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import struct
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
import zipfile
import zlib


CHUNK_BYTES = 1024 * 1024
MAX_ASSET_BYTES = 2 * 1024 * 1024 * 1024
MAX_MANIFEST_BYTES = 1024 * 1024
MAX_ZIP_DIRECTORY_BYTES = 32 * 1024 * 1024
READ_TIMEOUT_SECONDS = 60
TRANSFER_SECONDS = 900
DELIVERY_HOSTS = frozenset({
    "github.com", "raw.githubusercontent.com", "codeload.github.com",
    "objects.githubusercontent.com", "release-assets.githubusercontent.com",
})
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
COMMIT = re.compile(r"[0-9a-f]{40}\Z")
BASENAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+@~-]{0,254}\Z")


class SourceError(ValueError):
    """A safe diagnostic that contains no transport credentials or signed URL."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SourceError(message)


def validate_url(url: str, *, initial: bool = True) -> None:
    """Check every redirect before urllib makes its next request."""
    require(isinstance(url, str) and not any(ord(c) < 33 for c in url),
            "Download URL contains whitespace or control characters")
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError:
        raise SourceError("Invalid download URL") from None
    require(parsed.scheme == "https" and parsed.hostname in DELIVERY_HOSTS | {"api.github.com"},
            "Downloads must use an approved GitHub HTTPS host")
    require(parsed.username is None and parsed.password is None and port is None
            and parsed.netloc.lower() == parsed.hostname,
            "Download URL must not contain credentials or a port")
    require(not parsed.fragment, "Download URL must not contain a fragment")
    if parsed.hostname == "api.github.com":
        require(not parsed.query and re.fullmatch(
            r"/repos/[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9][A-Za-z0-9._-]*/releases/assets/[1-9][0-9]*",
            parsed.path), "GitHub API inputs must name an exact release asset ID")
        return
    if not initial:
        require(not parsed.query or parsed.hostname in
                ("objects.githubusercontent.com", "release-assets.githubusercontent.com"),
                "Only GitHub asset delivery redirects may contain a query")
        return  # GitHub's release CDN uses signed query parameters.
    require(not parsed.query, "Initial download URL must not contain a query")
    parts = unquote(parsed.path).split("/")[1:]
    require(all(p and p not in (".", "..") and "\\" not in p for p in parts),
            "Download URL has an unsafe path")
    host = parsed.hostname
    if host == "github.com":
        require(len(parts) == 6 and parts[2:4] == ["releases", "download"]
                and parts[4] != "latest", "Use a named GitHub release asset")
    elif host == "raw.githubusercontent.com":
        require(len(parts) >= 4 and COMMIT.fullmatch(parts[2]),
                "Raw GitHub inputs must name a full commit")
    elif host == "codeload.github.com":
        require(len(parts) == 4 and parts[2] in ("zip", "tar.gz")
                and COMMIT.fullmatch(parts[3]),
                "GitHub source archives must name a full commit")
    else:
        raise SourceError("Use the canonical GitHub URL, not a signed delivery URL")


class GitHubRedirectHandler(HTTPRedirectHandler):
    max_redirections = 5

    def redirect_request(self, request, response, code, message, headers, newurl):
        validate_url(newurl, initial=False)
        return super().redirect_request(request, response, code, message, headers, newurl)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "Manifest contains a duplicate JSON key")
        result[key] = value
    return result


def fields(value, required, optional=()):
    require(isinstance(value, dict) and set(required) <= set(value)
            and set(value) <= set(required) | set(optional),
            "Manifest has missing or unknown fields")


def size(value):
    require(type(value) is int and 0 < value <= MAX_ASSET_BYTES,
            "Manifest size must be a positive integer no larger than 2 GiB")


def digest(value):
    require(isinstance(value, str) and SHA256.fullmatch(value),
            "Manifest SHA256 must contain 64 lowercase hexadecimal characters")


def member_path(value):
    require(isinstance(value, str) and value and "\\" not in value
            and not any(ord(c) < 32 for c in value)
            and not value.startswith("/")
            and all(p not in ("", ".", "..") and ":" not in p for p in value.split("/"))
            and str(PurePosixPath(value)) == value, "Unsafe ZIP member path")


def load_manifest(path: Path) -> tuple[dict, str]:
    with Path(path).open("rb") as stream:
        raw = stream.read(MAX_MANIFEST_BYTES + 1)
    require(len(raw) <= MAX_MANIFEST_BYTES, "Manifest exceeds 1 MiB")
    try:
        manifest = json.loads(raw, object_pairs_hook=unique_object)
    except (UnicodeError, json.JSONDecodeError):
        raise SourceError("Manifest is not valid UTF-8 JSON") from None
    fields(manifest, ("schema_version", "sources"))
    require(type(manifest["schema_version"]) is int and manifest["schema_version"] == 1,
            "Unsupported manifest schema version")
    require(isinstance(manifest["sources"], list) and manifest["sources"],
            "Manifest must select at least one source")
    names = set()
    for source in manifest["sources"]:
        fields(source, ("url", "size", "format", "files"), ("sha256",))
        validate_url(source["url"])
        size(source["size"])
        require(source["format"] in ("file", "zip"), "Unsupported source format")
        if "sha256" in source:
            digest(source["sha256"])
        require(isinstance(source["files"], list) and source["files"],
                "Each source must select at least one file")
        paths = set()
        for entry in source["files"]:
            fields(entry, ("name", "size", "sha256", "provenance"),
                   ("path",) if source["format"] == "zip" else ())
            name = entry["name"]
            require(isinstance(name, str) and BASENAME.fullmatch(name) and name not in names,
                    "Output names must be safe, unique basenames")
            names.add(name)
            size(entry["size"])
            digest(entry["sha256"])
            try:
                provenance = urlsplit(entry["provenance"])
                safe_provenance = (isinstance(entry["provenance"], str)
                                   and provenance.scheme == "https" and provenance.hostname
                                   and provenance.username is None and provenance.password is None
                                   and provenance.port is None and not provenance.query
                                   and not any(ord(c) < 33 for c in entry["provenance"]))
            except (ValueError, TypeError, AttributeError):
                safe_provenance = False
            require(safe_provenance, "Provenance must be an HTTPS reference without credentials or query")
            if source["format"] == "zip":
                require("path" in entry, "ZIP files must name their exact member path")
                member_path(entry["path"])
                require(entry["path"] not in paths, "ZIP member selected more than once")
                paths.add(entry["path"])
        if source["format"] == "file":
            require(len(source["files"]) == 1 and "sha256" in source,
                    "Direct assets require one file and a whole-file SHA256")
            entry = source["files"][0]
            require((entry["size"], entry["sha256"]) == (source["size"], source["sha256"]),
                    "Direct asset and output size/SHA256 must agree")
    return manifest, hashlib.sha256(raw).hexdigest()


def copy_verified(stream, destination: Path, expected_size: int, expected_sha256: str) -> None:
    hasher = hashlib.sha256()
    total = 0
    with destination.open("wb") as output:
        while True:
            data = stream.read(min(CHUNK_BYTES, expected_size - total + 1))
            if not data:
                break
            total += len(data)
            require(total <= expected_size, "Input exceeds its locked size")
            hasher.update(data)
            output.write(data)
    require(total == expected_size and hasher.hexdigest() == expected_sha256,
            "Input size or SHA256 does not match its lock")


def cached_file(path: Path, destination: Path, entry: dict) -> bool:
    """Copy through one open descriptor; never trust cache filenames or symlinks."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                return False
            copy_verified(stream, destination, entry["size"], entry["sha256"])
        return True
    except (OSError, SourceError):
        destination.unlink(missing_ok=True)
        return False


def download(source: dict, destination: Path, *, github_token: str | None = None) -> None:
    """Bound bytes/time and sanitize errors, including signed CDN URL failures."""
    validate_url(source["url"])
    opener = build_opener(GitHubRedirectHandler())
    request = Request(source["url"], headers={"Accept-Encoding": "identity",
                                              "User-Agent": "sonic-github-sources/1"})
    if urlsplit(source["url"]).hostname == "api.github.com":
        request.add_header("Accept", "application/octet-stream")
        if github_token is not None:
            require(isinstance(github_token, str) and 0 < len(github_token) <= 4096
                    and all(33 <= ord(c) <= 126 for c in github_token),
                    "Invalid GitHub token environment value")
            # urllib excludes unredirected headers when creating a redirect request.
            request.add_unredirected_header("Authorization", "Bearer " + github_token)
    deadline = time.monotonic() + TRANSFER_SECONDS
    try:
        with opener.open(request, timeout=READ_TIMEOUT_SECONDS) as response:
            validate_url(response.geturl(), initial=False)
            require(response.status == 200, "GitHub asset did not return HTTP 200")
            length = response.headers.get("Content-Length")
            require(length is None or (length.isdecimal() and int(length) == source["size"]),
                    "GitHub asset Content-Length differs from its lock")
            total = 0
            with destination.open("wb") as output:
                while True:
                    require(time.monotonic() <= deadline, "GitHub download exceeded its deadline")
                    data = response.read(min(CHUNK_BYTES, source["size"] - total + 1))
                    if not data:
                        break
                    total += len(data)
                    require(total <= source["size"], "GitHub asset exceeds its locked size")
                    output.write(data)
            require(total == source["size"], "GitHub asset is shorter than its locked size")
    except HTTPError as error:
        raise SourceError(f"GitHub download failed with HTTP {error.code}; no alternate host attempted") from None
    except (URLError, OSError, HTTPException):
        raise SourceError("GitHub download failed; no alternate host attempted") from None


def source_files(path: Path, source: dict, stage: Path) -> None:
    """Verify a whole direct asset or only the explicitly locked ZIP members."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as stream:
            status = os.fstat(stream.fileno())
            require(stat.S_ISREG(status.st_mode) and status.st_size == source["size"],
                    "Cached source size or file type does not match its lock")
            if "sha256" in source:
                hasher = hashlib.sha256()
                total = 0
                while True:
                    chunk = stream.read(min(CHUNK_BYTES, source["size"] - total + 1))
                    if not chunk:
                        break
                    total += len(chunk)
                    require(total <= source["size"], "Source exceeds its locked size")
                    hasher.update(chunk)
                require(total == source["size"] and hasher.hexdigest() == source["sha256"],
                        "Source size or SHA256 does not match its lock")
                stream.seek(0)
            if source["format"] == "file":
                entry = source["files"][0]
                copy_verified(stream, stage / entry["name"], entry["size"], entry["sha256"])
                return
            # ZipFile materializes the central directory. Bound that allocation
            # before opening it; selected members have their own locked bounds.
            stream.seek(max(0, source["size"] - 65557))
            tail = stream.read(65557)
            end = tail.rfind(b"PK\x05\x06")
            require(end >= 0 and len(tail) - end >= 22, "ZIP end record is missing")
            record = struct.unpack("<4s4H2LH", tail[end:end + 22])
            require(record[1:3] == (0, 0) and record[3] == record[4] < 65535
                    and record[5] <= MAX_ZIP_DIRECTORY_BYTES
                    and record[6] < 0xffffffff and len(tail) - end == 22 + record[7],
                    "ZIP directory is too large, multipart or ZIP64")
            # ZipFile follows a ZIP64 locator even without legacy sentinel
            # values, replacing the directory size checked above. A maximum
            # comment puts the locator before our tail window; seek directly.
            end_offset = max(0, source["size"] - 65557) + end
            if end_offset >= 20:
                stream.seek(end_offset - 20)
                require(stream.read(4) != b"PK\x06\x07", "ZIP64 archives are unsupported")
            stream.seek(0)
            with zipfile.ZipFile(stream) as archive:
                for entry in source["files"]:
                    matches = [info for info in archive.infolist() if info.filename == entry["path"]]
                    require(len(matches) == 1, "Expected exactly one copy of each selected ZIP member")
                    info = matches[0]
                    require(info.orig_filename == entry["path"] and not info.flag_bits & 1
                            and stat.S_IFMT(info.external_attr >> 16) in (0, stat.S_IFREG)
                            and not info.is_dir() and info.file_size == entry["size"]
                            and info.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED),
                            "Selected ZIP member has an unsupported type, name, size or compression")
                    with archive.open(info) as member:
                        copy_verified(member, stage / entry["name"], entry["size"], entry["sha256"])
    except (zipfile.BadZipFile, RuntimeError, NotImplementedError, EOFError, zlib.error):
        raise SourceError("ZIP verification failed") from None


def atomic_copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as output:
            temporary = Path(output.name)
            with source.open("rb") as stream:
                for chunk in iter(lambda: stream.read(CHUNK_BYTES), b""):
                    output.write(chunk)
        temporary.chmod(0o644)
        temporary.replace(destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def prepare(manifest_path: Path, distdir: Path, cache_dir: Path, receipt: Path,
            repository_cache: Path | None = None, *, github_token: str | None = None) -> dict:
    manifest, manifest_sha256 = load_manifest(manifest_path)
    distdir, cache_dir, receipt = Path(distdir), Path(cache_dir), Path(receipt)
    require(receipt.resolve() != Path(manifest_path).resolve()
            and all(receipt.resolve() != (distdir / entry["name"]).resolve()
                    for source in manifest["sources"] for entry in source["files"]),
            "Receipt must not replace the manifest or a selected input")
    cache_dir.mkdir(parents=True, exist_ok=True)
    origins = {}
    with tempfile.TemporaryDirectory(prefix="github-sources-", dir=cache_dir) as temporary:
        stage = Path(temporary)
        payloads = stage / "payloads"
        payloads.mkdir()
        for index, source in enumerate(manifest["sources"]):
            missing = []
            for entry in source["files"]:
                candidates = [("distdir", distdir / entry["name"])]
                if repository_cache is not None:
                    candidates.append(("repository-cache", Path(repository_cache) / "content_addressable"
                                       / "sha256" / entry["sha256"] / "file"))
                for origin, candidate in candidates:
                    if cached_file(candidate, payloads / entry["name"], entry):
                        origins[entry["name"]] = origin
                        break
                else:
                    missing.append(entry["name"])
            if not missing:
                continue
            # Include all member locks in cache identity when no whole-ZIP digest exists.
            identity = hashlib.sha256(json.dumps(source, sort_keys=True).encode()).hexdigest()
            cached = cache_dir / (identity + ".asset")
            source_stage = stage / f"source-{index}"
            source_stage.mkdir()
            try:
                source_files(cached, source, source_stage)
                origin = "asset-cache"
            except (SourceError, OSError):
                fetched = stage / "download.asset"
                if github_token is None:
                    download(source, fetched)
                else:
                    download(source, fetched, github_token=github_token)
                source_files(fetched, source, source_stage)
                fetched.chmod(0o644)
                fetched.replace(cached)
                origin = "github"
            for name in missing:
                (source_stage / name).replace(payloads / name)
                origins[name] = origin
        # Integrity failures above publish no distdir changes. File replacement is
        # atomic individually; an I/O failure during this loop can leave a subset
        # of verified files. The caller must not start Bazel unless we succeed.
        for source in manifest["sources"]:
            for entry in source["files"]:
                atomic_copy(payloads / entry["name"], distdir / entry["name"])
        result = {
            "schema_version": 1,
            "manifest_sha256": manifest_sha256,
            "sources": [{"url": source["url"], "format": source["format"], "size": source["size"],
                         "whole_source_digest_declared": "sha256" in source}
                        for source in manifest["sources"]],
            "files": [{**entry, "source": origins[entry["name"]]}
                      for source in manifest["sources"] for entry in source["files"]],
        }
        staged_receipt = stage / "receipt.json"
        staged_receipt.write_text(json.dumps(result, indent=2) + "\n")
        atomic_copy(staged_receipt, receipt)
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--distdir", required=True, type=Path)
    parser.add_argument("--cache-dir", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--repository-cache", type=Path)
    parser.add_argument("--github-token-env", help="Explicit environment variable for GitHub release-asset API authentication")
    args = parser.parse_args(argv)
    try:
        github_token = None
        if args.github_token_env is not None:
            require(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,254}", args.github_token_env),
                    "Invalid GitHub token environment variable name")
            github_token = os.environ.get(args.github_token_env)
            require(github_token is not None and 0 < len(github_token) <= 4096
                    and all(33 <= ord(c) <= 126 for c in github_token),
                    "GitHub token environment variable is missing or invalid")
        prepare(args.manifest, args.distdir, args.cache_dir, args.receipt, args.repository_cache,
                github_token=github_token)
    except (SourceError, OSError) as error:
        print(f"github_sources: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
