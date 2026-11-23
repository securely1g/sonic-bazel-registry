"""Collect job-scoped HTTP evidence from Bazel commands that do not emit a BEP."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import time
import zipfile


def prepare(work: Path, jar: Path, mirrors: dict[str, str]) -> None:
    """Check that the supplied observer was built for this checkout."""
    source = Path(__file__).with_name("DebianHttpAudit.java")
    expected = hashlib.sha256(source.read_bytes()).hexdigest().encode()
    staged = work / "staged-http-audit.jar"
    shutil.copyfile(jar, staged)
    try:
        with zipfile.ZipFile(staged) as archive:
            if archive.read("META-INF/sonic-debian-http-audit.sha256") != expected:
                raise ValueError("Debian HTTP observer JAR belongs to another source revision")
    except (zipfile.BadZipFile, KeyError) as error:
        raise ValueError("Invalid Debian HTTP observer JAR") from error
    output = work / "http"
    output.mkdir(mode=0o700)
    options = {"output": str(output), **{f"mirror.{i}": value for i, value in enumerate(mirrors.values())}}
    with open(work / "http.properties", "x", opener=lambda p, flags: os.open(p, flags, 0o600)) as stream:
        for key, value in options.items():
            value = value.replace("\\", "\\\\").replace("\n", "\\n").replace("\r", "\\r")
            stream.write(f"{key}={value}\n")
    staged.replace(work / "http-audit.jar")


def final_record(path: Path) -> bool:
    # A healthy server can remain alive after a validation command. Look for its
    # acknowledgement of this job's flush, or its earlier normal shutdown.
    with path.open("rb") as stream:
        stream.seek(max(0, path.stat().st_size - 8192))
        for line in reversed(stream.readlines()):
            try:
                event = json.loads(line).get("event")
                if event in ("health", "shutdown", "installed"):
                    return event != "installed"
            except (AttributeError, ValueError):
                continue
    return False


def retain(work: Path, artifacts: Path) -> None:
    output = work / "http"
    if not output.is_dir():
        return
    (output / "flush").touch(mode=0o600)
    destination = artifacts / "download-traces" / "http"
    destination.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + 5
    while True:
        traces = [p for p in output.glob("http-*.jsonl")
                  if not p.is_symlink() and p.stem.removeprefix("http-").isdigit()]
        if all(final_record(path) for path in traces) or time.monotonic() >= deadline:
            break
        time.sleep(0.1)
    for path in traces:
        shutil.copyfile(path, destination / path.name)


def summarize(root: Path, counts, exceptions: set, failed_public: set) -> dict:
    directory = root / "download-traces" / "http"
    traces = sorted(directory.glob("http-*.jsonl"))
    healthy, gaps, public_requests = [], [], set()
    receipt = root / "private-mirrors.json"
    expected = receipt.is_file() and json.loads(receipt.read_text()).get("http_observer_expected", False)
    if expected and not directory.exists():
        gaps.append("Debian HTTP observer was unavailable")
    for path in traces:
        name = path.relative_to(root).as_posix()
        installed = closed = broken = False
        with path.open(errors="replace") as stream:
            for line in stream:
                try:
                    row = json.loads(line)
                    if row.get("schema_version") != 1 or row.get("pid") != int(path.stem.removeprefix("http-")):
                        raise ValueError("invalid JVM evidence identity")
                    event = row["event"]
                    if event == "installed":
                        broken |= installed and not closed
                        closed = False
                    if event in ("installed", "health", "shutdown"):
                        installed |= event == "installed"
                        closed |= event in ("health", "shutdown")
                        broken |= row["recording_failed"] or not row["handler_still_installed"]
                        continue
                    origin, kind = row["origin"], row["type"]
                    identity = row.get("object") or row.get("path", "(redirect destination)")
                    if origin not in ("public", "private") or event not in ("request", "response"):
                        raise ValueError("invalid HTTP observation")
                    if event == "request":
                        counts[(origin, kind, "HTTP request")] += 1
                        if origin == "public":
                            public_requests.add((kind, identity, name))
                        continue
                    status = int(row["status"])
                    outcome = f"HTTP {status} response"
                    counts[(origin, kind, outcome)] += 1
                    if origin == "public":
                        if status >= 400:
                            failed_public.add((kind, identity, name))
                        else:
                            exceptions.add((origin, kind, outcome, identity, name))
                except (AttributeError, KeyError, TypeError, ValueError):
                    broken = True
        (healthy if installed and closed and not broken else gaps).append(name)
    if directory.exists() and not traces:
        gaps.append("download-traces/http (no observed Bazel JVM)")
    return {"configured": directory.exists(), "complete": bool(healthy) and not gaps,
            "inputs": [p.relative_to(root).as_posix() for p in traces],
            "healthy": healthy, "gaps": gaps,
            "public_requests": [{"kind": k, "object": p, "evidence": n} for k, p, n in sorted(public_requests)]}
