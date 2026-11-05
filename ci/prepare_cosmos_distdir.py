#!/usr/bin/env python3
"""Supply APE 1.0.1's unchanged Cosmos 4.0.2 inputs through Bazel --distdir.

The original cosmo.zip endpoints reset connections in registry libteam CI.
The official jart/cosmopolitan 4.0.2 release ZIP contains byte-identical members.
Hashes below come from ape/cosmos/4.0.2.json in the BCR-pinned ape 1.0.1 source;
they, not the ZIP's transport URL, authenticate the two extracted files.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import stat
import tempfile
import time
from urllib.request import urlopen
import zipfile


VERSION = "4.0.2"
ARCHIVE_URL = "https://github.com/jart/cosmopolitan/releases/download/4.0.2/cosmos-4.0.2.zip"
ARCHIVE_BYTES = 402711738
ASSET_ID = 218247825
MEMBERS = {
    "assimilate": (656101, "93f63aac14046bc2530e4f98ff4dc7ade2e3a3aa3136ced3db598bf6b0026edc"),
    "ape-x86_64.elf": (9249, "7c1cf8b24e1b6dd6ad7da3817045d582ada146b4d6ec0c6a45bea830e3a65f4d"),
}


def verified(data: bytes, name: str) -> bytes:
    size, digest = MEMBERS[name]
    if len(data) != size or hashlib.sha256(data).hexdigest() != digest:
        raise ValueError(f"Cosmos {VERSION} {name}: size or SHA256 mismatch")
    return data


def read_cached(path: Path, name: str) -> bytes | None:
    if not path.is_file() or path.is_symlink():
        return None
    with path.open("rb") as stream:
        data = stream.read(MEMBERS[name][0] + 1)
    try:
        return verified(data, name)
    except ValueError:
        return None


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(data)
        temporary.chmod(0o644)
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def archive_members(path: Path) -> dict[str, bytes]:
    if path.stat().st_size != ARCHIVE_BYTES:
        raise ValueError("Unexpected Cosmos release ZIP size")
    result = {}
    with zipfile.ZipFile(path) as archive:
        for name, (size, _digest) in MEMBERS.items():
            entries = [info for info in archive.infolist() if info.filename == "bin/" + name]
            if len(entries) != 1:
                raise ValueError(f"Expected exactly one bin/{name} in Cosmos release ZIP")
            info = entries[0]
            kind = stat.S_IFMT(info.external_attr >> 16)
            if info.flag_bits & 1 or kind not in (0, stat.S_IFREG) or info.file_size != size:
                raise ValueError(f"Invalid Cosmos release member bin/{name}")
            # Never extract paths or execute files from the archive. Reading to
            # EOF also checks ZIP CRC; the locked SHA256 is the trust boundary.
            with archive.open(info) as stream:
                result[name] = verified(stream.read(size + 1), name)
    return result


def download_archive(destination: Path) -> dict[str, bytes]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as stream:
            temporary = Path(stream.name)
            deadline = time.monotonic() + 900
            # No credentials, automatic retries, or signed URL logging. The
            # socket timeout bounds each read; the deadline bounds the transfer.
            with urlopen(ARCHIVE_URL, timeout=60) as response:
                if response.status != 200:
                    raise ValueError("Cosmos release download did not return HTTP 200")
                length = response.headers.get("Content-Length")
                if length is not None and int(length) != ARCHIVE_BYTES:
                    raise ValueError("Unexpected Cosmos release Content-Length")
                total = 0
                while True:
                    if time.monotonic() > deadline:
                        raise TimeoutError("Cosmos release download exceeded 15 minutes")
                    data = response.read(min(1024 * 1024, ARCHIVE_BYTES - total + 1))
                    if not data:
                        break
                    total += len(data)
                    if total > ARCHIVE_BYTES:
                        raise ValueError("Cosmos release download exceeds expected size")
                    stream.write(data)
        result = archive_members(temporary)
        temporary.chmod(0o644)
        temporary.replace(destination)
        return result
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def prepare(distdir: Path, cache_dir: Path, receipt: Path,
            repository_cache: Path | None = None) -> dict:
    payloads = {}
    origins = {}
    for name, (_size, digest) in MEMBERS.items():
        candidates = [("distdir", distdir / name)]
        if repository_cache is not None:
            candidates.append(("repository-cache", repository_cache / "content_addressable" / "sha256" / digest / "file"))
        for origin, path in candidates:
            data = read_cached(path, name)
            if data is not None:
                payloads[name], origins[name] = data, origin
                break
    if len(payloads) != len(MEMBERS):
        archive = cache_dir / f"cosmos-{VERSION}.zip"
        if archive.is_file() and not archive.is_symlink():
            extracted, origin = archive_members(archive), "cached-release-zip"
        else:
            extracted, origin = download_archive(archive), "official-release-zip"
        for name, data in extracted.items():
            if name not in payloads:
                payloads[name], origins[name] = data, origin
    # Verify the complete set before publishing either member. Atomic replace
    # avoids exposing partial files; a failed second checksum changes neither.
    for name in MEMBERS:
        verified(payloads[name], name)
    for name, data in payloads.items():
        atomic_write(distdir / name, data)
    result = {
        "version": VERSION,
        "archive_url": ARCHIVE_URL,
        "release_asset_id": ASSET_ID,
        "whole_archive_digest_verified": False,
        "members": [{"name": name, "zip_member": "bin/" + name,
                     "bytes": size, "sha256": digest, "source": origins[name]}
                    for name, (size, digest) in MEMBERS.items()],
    }
    atomic_write(receipt, (json.dumps(result, indent=2) + "\n").encode())
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--distdir", required=True, type=Path)
    parser.add_argument("--cache-dir", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--repository-cache", type=Path)
    args = parser.parse_args()
    prepare(args.distdir, args.cache_dir, args.receipt, args.repository_cache)


if __name__ == "__main__":
    main()
