"""Keep private download locations out of published CI diagnostics and artifacts.

This is an accidental-disclosure guard, not isolation from code executing in a
job which receives the mirror configuration. Payloads are inspected, never
rewritten; only the documented diagnostic text formats may be redacted.
"""
from __future__ import annotations

import base64
import bz2
import contextlib
import gzip
import hashlib
import io
import json
import lzma
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tarfile
import tempfile
from urllib.parse import quote, quote_plus, urlsplit
import zipfile
import zlib


CHUNK_SIZE = 1024 * 1024
MAX_ARCHIVE_DEPTH = 8
MARKER = "[private-mirror]"
# Cross-toolchain graph preparation and runtime probes retain command streams
# separately; these are diagnostics just like build.log and test.log.
TEXT_SUFFIXES = {".log", ".stderr", ".stdout", ".json", ".jsonl", ".xml"}


class PrivacyError(ValueError):
    """A generic error deliberately containing no private input or filename."""


class TemporaryBudget:
    """Cap block-rounded live file extents, with separate filesystem headroom."""

    def __init__(self, directory: Path, *, maximum_bytes: int, minimum_free_bytes: int):
        if (type(maximum_bytes) is not int or maximum_bytes <= 0 or
                type(minimum_free_bytes) is not int or minimum_free_bytes < 0):
            raise PrivacyError("Invalid scanner temporary-space budget")
        self.directory = Path(directory)
        try:
            if (not self.directory.is_dir() or self.directory.is_symlink() or
                    self.directory.resolve() != self.directory.absolute()):
                raise PrivacyError("Unsafe scanner temporary directory")
            self.device = self.directory.stat().st_dev
        except OSError:
            raise PrivacyError("Cannot inspect scanner temporary filesystem") from None
        self.maximum_bytes, self.minimum_free_bytes = maximum_bytes, minimum_free_bytes
        self.live_bytes = self.peak_bytes = self.open_files = self.peak_open_files = 0

    def _free(self, additional=0):
        usage = os.statvfs(self.directory)
        if usage.f_bavail * usage.f_frsize < self.minimum_free_bytes + additional:
            raise PrivacyError("Scanner filesystem headroom is insufficient")

    def preflight(self, artifacts: Path):
        if artifacts.stat().st_dev != self.device:
            raise PrivacyError("Scanner evidence and temporaries use different filesystems")
        self._free()

    def _open(self, stream):
        if os.fstat(stream.fileno()).st_dev != self.device:
            raise PrivacyError("Scanner temporary uses an unexpected filesystem")
        self._free()
        counted = _BudgetedFile(stream, self)
        self.open_files += 1
        self.peak_open_files = max(self.peak_open_files, self.open_files)
        return counted

    def _reserve(self, growth):
        if self.live_bytes + growth > self.maximum_bytes:
            raise PrivacyError("Scanner temporary-space budget exceeded")
        self._free(growth)
        self.live_bytes += growth
        self.peak_bytes = max(self.peak_bytes, self.live_bytes)

    def _closed(self, stream):
        self.live_bytes -= stream.accounted_bytes
        self.open_files -= 1

    def usage(self):
        return {"maximum_bytes": self.maximum_bytes, "minimum_free_bytes": self.minimum_free_bytes,
                "live_bytes": self.live_bytes, "peak_bytes": self.peak_bytes,
                "open_files": self.open_files, "peak_open_files": self.peak_open_files}


class _BudgetedFile:
    def __init__(self, stream, budget):
        self.stream, self.budget = stream, budget
        self.accounted_bytes = 0
        self.block_size = os.fstatvfs(stream.fileno()).f_frsize

    def write(self, value):
        end = self.stream.tell() + len(value)
        rounded = ((end + self.block_size - 1) // self.block_size) * self.block_size
        growth = max(0, rounded - self.accounted_bytes)
        self.budget._reserve(growth)
        self.accounted_bytes += growth
        written = self.stream.write(value)
        if written != len(value):
            raise PrivacyError("Scanner temporary write was incomplete")
        return written

    def __getattr__(self, name):
        return getattr(self.stream, name)


class _MemberReader:
    """Limit reads to one ar member without loading its contents into memory."""

    def __init__(self, stream, size: int):
        self.stream, self.remaining = stream, size

    def read(self, size: int = -1) -> bytes:
        size = self.remaining if size < 0 else min(size, self.remaining)
        value = self.stream.read(size)
        self.remaining -= len(value)
        return value


class Redactor:
    def __init__(self, urls: list[str], *, temporary_budget: TemporaryBudget | None = None):
        self.temporary_budget = temporary_budget
        values = set()
        for url in urls:
            if not url:
                continue
            try:
                parsed = urlsplit(url)
                if not parsed.hostname:
                    raise ValueError
                seeds = {url, url.rstrip("/"), parsed.netloc, parsed.hostname,
                         parsed.hostname.encode("idna").decode()}
            except (ValueError, UnicodeError):
                raise PrivacyError("Invalid private mirror location") from None
            for value in seeds:
                if not value:
                    continue
                values.update((value, quote(value, safe=""), quote_plus(value, safe=""),
                               value.replace("/", r"\/"), re.escape(value)))
        values.update(json.dumps(value, ensure_ascii=True)[1:-1] for value in tuple(values))
        self.patterns = tuple(sorted(values, key=lambda value: (-len(value), value)))
        self._raw_patterns = frozenset(value.encode().lower() for value in values)
        self.max_pattern_length = max(map(len, self._raw_patterns), default=1)
        self._text = re.compile("|".join(re.escape(value) for value in self.patterns), re.I) if values else None
        self._bytes = re.compile(b"|".join(re.escape(value.encode()) for value in self.patterns), re.I) if values else None

    @contextlib.contextmanager
    def _temporary_file(self, *, directory=None, named=False):
        budget = self.temporary_budget
        options = {"dir": directory or (budget.directory if budget else None)}
        if budget:
            # Writes are accounted before reaching the filesystem, not delayed
            # in a buffered file whose flush could outlive a nested spool.
            options["buffering"] = 0
        if named:
            options.update(prefix=".mirror-redaction-", delete=False)
        raw = (tempfile.NamedTemporaryFile if named else tempfile.TemporaryFile)(**options)
        counted = None
        try:
            counted = budget._open(raw) if budget else None
            yield counted or raw
        finally:
            try:
                raw.close()
            finally:
                if named:
                    Path(raw.name).unlink(missing_ok=True)
                if counted is not None and raw.closed:
                    budget._closed(counted)

    def redact(self, text: str) -> str:
        return self._text.sub(MARKER, text) if self._text else text

    def redact_bytes(self, data: bytes) -> bytes:
        return self._bytes.sub(MARKER.encode(), data) if self._bytes else data

    def mask_github(self) -> None:
        if os.environ.get("GITHUB_ACTIONS") != "true":
            return
        for value in self.patterns:
            # Workflow commands require escaping their data rather than shell
            # interpolation. These commands register values; they are not logs.
            escaped = value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
            print("::add-mask::" + escaped, flush=True)

    def _check_text(self, value: str) -> None:
        if self._text and self._text.search(value):
            raise PrivacyError("Private mirror location remains in validation evidence")

    def _scan_raw(self, stream, first: bytes = b"", copy=None) -> None:
        tail = b""
        part = first
        while part:
            # bytes.lower() uses the same ASCII case folding as bytes re.I.
            # Literal searches avoid running the regex alternation on large binaries.
            folded = tail + part.lower()
            if any(pattern in folded for pattern in self._raw_patterns):
                raise PrivacyError("Private mirror location remains in validation evidence")
            if copy is not None:
                copy.write(part)
            tail = folded[-(self.max_pattern_length - 1):] if self.max_pattern_length > 1 else b""
            part = stream.read(CHUNK_SIZE)

    @staticmethod
    def _format(prefix: bytes, name: str) -> str | None:
        # Empty OCI whiteouts and placeholders have no payload to decode,
        # even when their names retain a deleted file's archive extension.
        if not prefix:
            return None
        if prefix.startswith(b"\x1f\x8b"):
            return "gzip"
        if prefix.startswith(b"BZh"):
            return "bz2"
        if prefix.startswith(b"\xfd7zXZ\x00"):
            return "xz"
        if prefix.startswith(b"\x28\xb5\x2f\xfd"):
            return "zstd"
        if prefix.startswith((b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")):
            return "zip"
        if prefix.startswith(b"!<arch>\n"):
            return "ar"
        if prefix[257:262] == b"ustar" or name.endswith(".tar"):
            return "tar"
        if prefix.startswith((b"7z\xbc\xaf\x27\x1c", b"Rar!", b"!<thin>\n", b"\x04\x22\x4d\x18")):
            raise PrivacyError("Unsupported archive in private-mirror validation evidence")
        if name.lower().endswith((".gz", ".tgz", ".bz2", ".xz", ".zst", ".zip", ".7z", ".rar", ".lz4", ".lz", ".lzma")):
            raise PrivacyError("Unrecognized archive in private-mirror validation evidence")
        return None

    def _scan_stream(self, stream, name: str = "", depth: int = 0) -> None:
        if depth > MAX_ARCHIVE_DEPTH:
            raise PrivacyError("Validation evidence exceeds the archive nesting limit")
        prefix = stream.read(512)
        try:
            kind = self._format(prefix, name)
        except PrivacyError as error:
            # Retain only controlled categories and a full-name digest. Even
            # checked archive names and raw content stay out of public errors.
            suffix = next((value for value in (".gz", ".tgz", ".bz2", ".xz", ".zst", ".zip",
                                               ".7z", ".rar", ".lz4", ".lz", ".lzma")
                           if name.lower().endswith(value)), "none")
            prefix_class = ("zero-filled" if not any(prefix) else
                            "ascii-text" if all(value in (9, 10, 13) or 32 <= value <= 126
                                                for value in prefix) else "other")
            detail = {"depth": depth, "suffix": suffix, "prefix_bytes": len(prefix),
                      "prefix_class": prefix_class,
                      "member_sha256": hashlib.sha256(name.encode("utf-8", "surrogatepass")).hexdigest()}
            raise PrivacyError(f"{error}; archive-format {json.dumps(detail, sort_keys=True)}") from None
        if kind is None:
            self._scan_raw(stream, prefix)
            return
        # Archive readers may need seeking. Spool only container formats, on
        # disk; regular ELF/debug files are scanned directly in bounded chunks.
        with self._temporary_file() as data:
            self._scan_raw(stream, prefix, data)
            data.seek(0)
            if kind in ("gzip", "bz2", "xz"):
                decoded = (gzip.GzipFile(fileobj=data, mode="rb") if kind == "gzip" else
                           {"bz2": bz2.BZ2File, "xz": lzma.LZMAFile}[kind](data, "rb"))
                with decoded:
                    self._scan_stream(decoded, depth=depth + 1)
            elif kind == "zstd":
                executable = shutil.which("zstd")
                if not executable:
                    raise PrivacyError("A required archive scanner is unavailable")
                process = subprocess.Popen([executable, "--quiet", "--decompress", "--stdout"],
                                           stdin=data, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                try:
                    self._scan_stream(process.stdout, depth=depth + 1)
                    if process.wait(timeout=30):
                        raise PrivacyError("Cannot inspect compressed validation evidence")
                finally:
                    process.stdout.close()
                    if process.poll() is None:
                        process.kill()
                        process.wait()
            elif kind == "tar":
                with tarfile.open(fileobj=data, mode="r:") as archive:
                    for member in archive:
                        self._check_text(member.name)
                        self._check_text(member.linkname)
                        if member.isfile():
                            with archive.extractfile(member) as contents:
                                self._scan_stream(contents, member.name, depth + 1)
            elif kind == "zip":
                with zipfile.ZipFile(data) as archive:
                    for member in archive.infolist():
                        self._check_text(member.filename)
                        if member.flag_bits & 1:
                            raise PrivacyError("Encrypted validation evidence cannot be inspected")
                        if not member.is_dir():
                            with archive.open(member) as contents:
                                self._scan_stream(contents, member.filename, depth + 1)
            else:
                data.seek(8)
                while header := data.read(60):
                    if len(header) != 60 or header[58:] != b"`\n":
                        raise PrivacyError("Invalid ar archive in validation evidence")
                    size = int(header[48:58])
                    if size < 0:
                        raise PrivacyError("Invalid ar archive in validation evidence")
                    start = data.tell()
                    member_name = header[:16].decode("ascii").strip().rstrip("/")
                    if member_name.startswith("#1/"):
                        length = int(member_name[3:])
                        if length > size or length < 0:
                            raise PrivacyError("Invalid ar archive in validation evidence")
                        member_name = data.read(length).decode("utf-8")
                        size -= length
                    self._check_text(member_name)
                    self._scan_stream(_MemberReader(data, size), member_name, depth + 1)
                    data.seek(start + int(header[48:58]) + int(header[48:58]) % 2)

    def _scrub(self, path: Path) -> dict | None:
        before, after = hashlib.sha256(), hashlib.sha256()
        changed = False
        with self._temporary_file(directory=path.parent, named=True) as output:
            temporary = Path(output.name)
            try:
                pending = b""
                with path.open("rb") as source:
                    while True:
                        part = source.read(CHUNK_SIZE)
                        before.update(part)
                        pending += part
                        boundary = len(pending) if not part else max(0, len(pending) - self.max_pattern_length + 1)
                        # A complete match beginning in the safe prefix may
                        # extend into the overlap; retain no partial secret.
                        end = boundary
                        for match in self._bytes.finditer(pending):
                            if match.start() >= boundary:
                                break
                            end = max(end, match.end())
                        raw = pending[:end]
                        clean = self.redact_bytes(raw)
                        changed |= clean != raw
                        output.write(clean)
                        after.update(clean)
                        pending = pending[end:]
                        if not part:
                            break
                output.flush()
                if changed:
                    os.chmod(temporary, stat.S_IMODE(path.stat().st_mode))
                    os.replace(temporary, path)
                    return {"original_sha256": before.hexdigest(), "sanitized_sha256": after.hexdigest()}
                return None
            finally:
                temporary.unlink(missing_ok=True)

    def _scan_bep_files(self, value) -> None:
        """Inspect protobuf File.contents bytes, which JSON encodes as base64."""
        if isinstance(value, list):
            for child in value:
                self._scan_bep_files(child)
        elif isinstance(value, dict):
            if "contents" in value:
                encoded = value["contents"]
                if not isinstance(encoded, str):
                    raise PrivacyError("Cannot inspect inline Bazel file contents")
                # Protobuf JSON accepts standard and URL-safe base64, with or
                # without padding. File.name may be omitted from the event.
                decoded = base64.b64decode(encoded + "=" * (-len(encoded) % 4),
                                           altchars=b"-_", validate=True)
                name = value.get("name", "")
                self._scan_stream(io.BytesIO(decoded), name if isinstance(name, str) else "")
            for child in value.values():
                self._scan_bep_files(child)

    def _scrub_bep(self, path: Path) -> dict | None:
        """Remove fragmented Progress output, retaining the useful event graph."""
        before, after = hashlib.sha256(), hashlib.sha256()
        removed = 0
        with self._temporary_file(directory=path.parent, named=True) as output:
            temporary = Path(output.name)
            try:
                with path.open("rb") as source:
                    for raw in source:
                        before.update(raw)
                        event = json.loads(raw)
                        if not isinstance(event, dict):
                            raise PrivacyError("Invalid Bazel event evidence")
                        progress = event.get("progress")
                        changed = False
                        if isinstance(progress, dict):
                            for field in ("stdout", "stderr"):
                                if field in progress:
                                    del progress[field]
                                    changed = True
                                    removed += 1
                        self._scan_bep_files(event)
                        # Full sanitized build.log/test.log remains available;
                        # concatenating BEP Progress fragments must not recover
                        # a URL split across independent event records.
                        clean = (json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n").encode() if changed else raw
                        output.write(clean)
                        after.update(clean)
                output.flush()
                if removed:
                    os.chmod(temporary, stat.S_IMODE(path.stat().st_mode))
                    os.replace(temporary, path)
                    return {"original_sha256": before.hexdigest(), "sanitized_sha256": after.hexdigest(),
                            "bep_progress_fields_removed": removed}
                return None
            finally:
                temporary.unlink(missing_ok=True)

    def _write_bytes(self, path: Path, payload: bytes) -> None:
        # Replacing the directory entry avoids mutating hard-linked source
        # diagnostics or following an existing receipt symlink.
        with self._temporary_file(directory=path.parent, named=True) as output:
            temporary = Path(output.name)
            try:
                output.write(payload)
                output.flush()
                if path.exists():
                    os.chmod(temporary, stat.S_IMODE(path.stat().st_mode))
                os.replace(temporary, path)
            finally:
                temporary.unlink(missing_ok=True)

    def _update_test_index(self, root: Path, changes: list[dict]) -> None:
        path = root / "test-results.json"
        if not path.is_file():
            return
        original = path.read_bytes()
        index = json.loads(original)
        if not isinstance(index, list):
            return
        changed = {item["path"]: item for item in changes}
        updated = False
        for test in index:
            for record in test.get("files", []) if isinstance(test, dict) else []:
                relative = record.get("path") if isinstance(record, dict) else None
                if isinstance(relative, str) and relative in changed:
                    record["sha256"] = changed[relative]["sanitized_sha256"]
                    record["size"] = (root / relative).stat().st_size
                    updated = True
        if updated:
            payload = (json.dumps(index, indent=2) + "\n").encode()
            self._write_bytes(path, payload)
            record = changed.get("test-results.json")
            if record is None:
                record = {"path": "test-results.json", "original_sha256": hashlib.sha256(original).hexdigest()}
                changes.append(record)
            record["sanitized_sha256"] = hashlib.sha256(payload).hexdigest()

    def write_checked_text(self, path: Path, value: str) -> None:
        """Atomically publish a sanitized report after checking it for private values."""
        self._check_text(value)
        self._write_bytes(path, value.encode())

    def scrub_and_scan(self, artifacts: Path) -> None:
        """Redact diagnostic text, then refuse publication if any location remains."""
        if not self.patterns or not artifacts.exists():
            return
        try:
            if artifacts.is_symlink() or not artifacts.is_dir():
                raise PrivacyError("Unsafe validation evidence directory")
            root = artifacts.resolve()
            if self.temporary_budget:
                self.temporary_budget.preflight(root)
            regular = []
            directories = [root]
            while directories:
                directory = directories.pop()
                for path in directory.iterdir():
                    self._check_text(path.relative_to(root).as_posix())
                    mode = path.lstat().st_mode
                    if stat.S_ISLNK(mode):
                        self._check_text(os.readlink(path))
                        if not path.resolve().is_relative_to(root):
                            raise PrivacyError("Validation evidence symlink escapes its directory")
                    elif stat.S_ISDIR(mode):
                        directories.append(path)
                    elif stat.S_ISREG(mode):
                        regular.append(path)
                    else:
                        raise PrivacyError("Unsupported validation evidence file type")
            changes = []
            for path in regular:
                relative = path.relative_to(root).as_posix()
                try:
                    receipt = self._scrub_bep(path) if path.name.endswith("-events.jsonl") else None
                    if path.suffix in TEXT_SUFFIXES or path.name.endswith("MODULE.bazel.lock"):
                        text_receipt = self._scrub(path)
                        if text_receipt:
                            receipt = ({**receipt, "sanitized_sha256": text_receipt["sanitized_sha256"]}
                                       if receipt else text_receipt)
                    if receipt:
                        changes.append({"path": relative, **receipt})
                    with path.open("rb") as stream:
                        self._scan_stream(stream, path.name)
                except PrivacyError as error:
                    # The outer relative name passed _check_text above. Never
                    # include an untrusted archive member or raw OS exception;
                    # JSON quoting keeps control characters on one log line.
                    raise PrivacyError(f"{error} (artifact {json.dumps(relative)})") from None
            if changes:
                self._update_test_index(root, changes)
                self._write_bytes(root / "mirror-redaction.json", (json.dumps({
                    "diagnostics_sanitized": True,
                    "payloads_modified": False,
                    "files": changes,
                }, indent=2) + "\n").encode())
        except PrivacyError:
            raise
        except (OSError, ValueError, EOFError, RuntimeError, tarfile.TarError, zipfile.BadZipFile,
                lzma.LZMAError, zlib.error,
                subprocess.SubprocessError):
            # Archive readers and OS exceptions can embed filenames and URLs.
            raise PrivacyError("Could not inspect private-mirror validation evidence") from None
