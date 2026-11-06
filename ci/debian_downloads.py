"""Retain Debian fetch origins, including Bazel commands before build and test."""
from __future__ import annotations

from collections import Counter
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit
from uuid import uuid4

MARKER = "[private-mirror]"
COMMANDS = {"fetch", "mod", "info", "query", "cquery", "aquery", "build", "test", "run"}
# Bazel 8.5.1 accepts these startup options as either --name=value or
# --name value. A startup value can even be the name of a Bazel command.
STARTUP_WITH_VALUE = {
    "--bazelrc", "--connect_timeout_secs", "--digest_function", "--experimental_cgroup_parent",
    "--failure_detail_out", "--host_jvm_args", "--install_base", "--io_nice_level",
    "--local_startup_timeout_secs", "--macos_qos_class", "--max_idle_secs", "--output_base",
    "--output_user_root", "--server_javabase", "--server_jvm_out",
}
APT_GET = re.compile(r"^Get:\d+\s+(\S+)\s+(.+?)\s+\[[^]]+\]")


def location(url: str, private_roots: dict[str, set[str]] | None = None) -> tuple[str, str, str] | None:
    """Return origin, object type and a public-relative identity; omit endpoint credentials."""
    marked_base = url.startswith(MARKER)
    parsed = urlsplit(("https://private.invalid/" + url[len(MARKER):].lstrip("/")) if marked_base
                      else url.replace(MARKER, "private.invalid"))
    host = parsed.hostname or ""
    if parsed.scheme not in ("http", "https") or host in ("localhost", "127.0.0.1", "::1"):
        return None
    roots = (private_roots or {}).get(host, set())
    private = marked_base or host == "private.invalid" or bool(roots)
    path = parsed.path
    if roots:
        # A deployment may mount the archive below a private path prefix.
        # Retain only the path relative to that mount in public evidence.
        prefix = next((p for p in sorted(roots, key=len, reverse=True) if path.startswith(p + "/")), None)
        path = path[len(prefix):] if prefix is not None else "/private-object"
    debian = host == "debian.org" or host.endswith(".debian.org")
    if path.endswith((".deb", ".udeb", ".ddeb")):
        kind = "binary"
    elif not (debian or private):
        return None
    elif re.fullmatch(r"/file/[0-9a-fA-F]{40}", path):
        kind = "content-addressed"
    elif "/dists/" in path:
        kind = "index"
    elif "/pool/" in path and re.search(r"\.(?:dsc|diff\.gz|tar\.(?:gz|bz2|xz|lzma|zst))$", path):
        kind = "source"
    else:
        kind = "other"
    return ("private" if private else "public", kind, path)


def trace(bazel: str, artifacts: Path, workspace: Path, map_file: Path, args: list[str]) -> int:
    """Run Bazel as supplied. Capture only Debian fetch events for commands without a BEP."""
    arguments = iter(args)
    command = None
    for arg in arguments:
        if arg in STARTUP_WITH_VALUE:
            next(arguments, None)
        elif not arg.startswith("-"):
            command = arg
            break
    if command not in COMMANDS:
        os.execvp(bazel, [bazel, *args])
    boundary = args.index("--") if "--" in args else len(args)
    options = args[:boundary]
    config_flags = ("--experimental_downloader_config", "--downloader_config")
    explicit_config = None
    for index, arg in enumerate(options):
        flag, separator, value = arg.partition("=")
        if flag in config_flags:
            explicit_config = value if separator else (options[index + 1] if index + 1 < len(options) else "")
    # Commands such as the cross provider and cold-cache tests can spawn Bazel
    # before the main build. Supply the private default even when no caller
    # forwards flags. Deliberate fixture-specific routing takes precedence.
    if explicit_config is None or Path(explicit_config).resolve() == Path(__file__).with_name("source_mirrors.cfg"):
        options.append(f"--experimental_downloader_config={workspace / 'downloader.cfg'}")
    argv = [*options, *args[boundary:]]
    if any(arg.partition("=")[0] == "--build_event_json_file" for arg in options):
        os.execvp(bazel, [bazel, *argv])
    preferred = json.loads(map_file.read_text())["mirrors"].values()
    private_roots = {}
    for url in preferred:
        parsed = urlsplit(url)
        private_roots.setdefault(parsed.hostname, set()).add(parsed.path.rsplit("/archive/", 1)[0])
    evidence = artifacts / "download-traces"
    evidence.mkdir(parents=True, exist_ok=True)
    # Collect the full event stream outside uploaded evidence and keep only
    # the fetch outcome and redacted object path. Unique files support nested
    # invocations of the Rust preparer and parallel fixture processes.
    with tempfile.TemporaryDirectory(dir=workspace, prefix="bep-") as directory:
        raw = Path(directory) / "events"
        argv.insert(len(options), f"--build_event_json_file={raw}")
        result = subprocess.run([bazel, *argv])
        with (evidence / f"{command}-{uuid4().hex}-events.jsonl").open("w") as out:
            finished = False
            if raw.exists():
                with raw.open("rb") as inp:
                    for line in inp:
                        try:
                            event = json.loads(line)
                        except ValueError:
                            continue  # The final record can be truncated on a failed action.
                        identifier = event.get("id", {})
                        finished |= "buildFinished" in identifier
                        url = identifier.get("fetch", {}).get("url", "")
                        obj = location(url, private_roots) if url else None
                        if obj:
                            origin, _, path = obj
                            sanitized = (MARKER if origin == "private" else "https://" + urlsplit(url).hostname) + path
                            record = {"id": {"fetch": {"url": sanitized}},
                                      "fetch": {"success": event.get("fetch", {}).get("success", False)}}
                            out.write(json.dumps(record) + "\n")
            out.write(json.dumps({"registryFetchCoverage": {"command": command, "exit": result.returncode,
                                                            "finished_event": finished}}) + "\n")
    return result.returncode if result.returncode >= 0 else 128 - result.returncode


def report(root: Path) -> dict:
    """Read sanitized evidence. APT Get activity and Bazel FetchEvents have distinct semantics."""
    counts = Counter()
    exceptions = set()
    incomplete = set()
    public_probes = set()
    inputs = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue
        bep = path.name.endswith("-events.jsonl")
        if not bep and not (path.name.endswith(".apt.log") or path.name == "apt.log"):
            continue
        name = path.relative_to(root).as_posix()
        inputs.append(name)
        finished = False
        with path.open(errors="replace") as stream:
            for line in stream:
                if bep:
                    try:
                        event = json.loads(line)
                    except ValueError:
                        incomplete.add(name)
                        continue
                    coverage = event.get("registryFetchCoverage")
                    finished |= bool(coverage and coverage["finished_event"]) or "buildFinished" in event.get("id", {})
                    url = event.get("id", {}).get("fetch", {}).get("url", "")
                    item = location(url) if url else None
                    if item is None:
                        continue
                    origin, kind, identity = item
                    outcome = "successful candidate" if event.get("fetch", {}).get("success") else "failed candidate"
                else:
                    match = APT_GET.match(line)
                    if not match:
                        continue
                    url, description = match.groups()
                    if url.startswith(("file:", "copy:")):
                        continue  # APT reads local mirror lists and cached archives without a transfer.
                    item = location(url)
                    if item is None:
                        # Native APT mirror lists can print a logical source URI.
                        # Retain that uncertainty instead of calling the fetch private.
                        origin = "unattributed"
                    else:
                        origin = item[0]
                    parts = description.split()
                    binary = len(parts) >= 4 and parts[-2] in ("amd64", "arm64", "armhf", "all")
                    kind = "binary" if binary else "metadata"
                    identity = " ".join(parts[-3:]) if binary else description
                    outcome = "APT Get"
                counts[(origin, kind, outcome)] += 1
                if origin != "private":
                    if outcome == "failed candidate":
                        public_probes.add((kind, identity, name))
                    else:
                        exceptions.add((origin, kind, outcome, identity, name))
        if bep and not finished:
            incomplete.add(name)
    return {"inputs": inputs, "incomplete_traces": sorted(incomplete),
            "failed_public_candidates": [{"kind": k, "object": obj, "evidence": evidence}
                                         for k, obj, evidence in sorted(public_probes)],
            "counts": [{"origin": a, "kind": b, "outcome": c, "count": n}
                       for (a, b, c), n in sorted(counts.items())],
            "exceptions": [{"origin": a, "kind": b, "outcome": c, "object": d, "evidence": e}
                           for a, b, c, d, e in sorted(exceptions)]}


if __name__ == "__main__":
    sys.exit(trace(sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]), sys.argv[5:]))
