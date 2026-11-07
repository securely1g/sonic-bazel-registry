#!/usr/bin/env python3
"""Check the selected libteam owner's declared config input, then restore it.

Run this exported source file from a consumer checkout with its existing Bazel
entry point and cache flags. This acceptance command is not a Bazel test that
starts another server. Adapted from sonic-buildimage 233bde227dc62712bb3324ab4249cfbf145de893.
"""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time


OUTPUTS = (
    "libteam_runtime", "libteam_runtime.debug_symbols",
    "libteamdctl_runtime", "libteamdctl_runtime.debug_symbols",
    "libteam_utils_runtime", "libteam_utils_runtime.debug_symbols",
    "libteam_dev", "runtime_packages.json", "library_runtime_packages.json",
)
SCRIPT_LABEL = "@libteam//:bazel/verify_rebuild.py"
NEEDLE = b'#define PACKAGE_VERSION "@PACKAGE_VERSION@"'
EDIT = b'#define PACKAGE_VERSION "1.31-input-probe"'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def successful_events(path):
    if not path.is_file() or not path.stat().st_size:
        raise ValueError("missing build-event evidence")
    finished = []
    with path.open() as stream:
        for line in stream:
            if line.strip():
                event = json.loads(line)
                if "buildFinished" in event.get("id", {}):
                    finished.append(event.get("finished", {}))
    # Bazel 8.5.1 uses protobuf JSON, which omits the default numeric zero.
    result = finished[0] if len(finished) == 1 else {}
    exit_code = result.get("exitCode", {})
    code = exit_code.get("code", 0)
    if (len(finished) != 1 or result.get("overallSuccess") is not True
            or exit_code.get("name") != "SUCCESS" or type(code) is not int or code != 0):
        raise ValueError("build-event evidence lacks one successful buildFinished event")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bazel", required=True, help="Existing consumer Bazel entry point")
    parser.add_argument("--bazel-arg", action="append", default=[])
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    # Preflight failures must not leave a previous invocation's passed receipt.
    (args.output / "rebuild.json").unlink(missing_ok=True)
    script = Path(__file__).resolve()
    owner = script.parent.parent
    config = script.parent / "config.h.in"
    original = config.read_bytes()
    # Reject commented, duplicated or already modified probes before any build.
    if original.count(NEEDLE) != 1 or original.splitlines().count(NEEDLE) != 1:
        raise ValueError("config probe requires the reviewed PACKAGE_VERSION input")
    targets = ["@libteam//:" + name for name in OUTPUTS]
    sources = {str(path.relative_to(owner)): sha(path) for path in (
        owner / "MODULE.bazel", owner / "BUILD.bazel", config, script,
    )}
    records = []
    commands = []
    status = "failed"
    execution_root = None
    registry_files = {}

    def run(command, *, capture=False):
        commands.append(command)
        return subprocess.run(command, check=True, **(
            {"capture_output": True, "text": True} if capture else {}))

    def query(expression):
        result = run([args.bazel, "cquery", *args.bazel_arg, expression,
                      "--output=files"], capture=True)
        return [execution_root / line for line in result.stdout.splitlines() if line.strip()]

    def build(phase):
        start = time.monotonic()
        events = args.output / (phase + "-events.json")
        # Never accept evidence left by a previous execution in this directory.
        events.unlink(missing_ok=True)
        run([args.bazel, "build", "--jobs=2", *args.bazel_arg,
             "--build_event_json_file=" + str(events), *targets])
        successful_events(events)
        outputs = query("set(" + " ".join(targets) + ")")
        if len(outputs) != len(targets) or len({path.resolve() for path in outputs}) != len(targets):
            raise ValueError("expected nine distinct owner archive/metadata outputs")
        if not all(path.is_file() for path in outputs):
            raise ValueError("missing owner output")
        digests = {str(path): sha(path) for path in outputs}
        records.append({
            "phase": phase, "seconds": round(time.monotonic() - start, 3),
            "outputs_sha256": digests, "config_sha256": sha(config),
            "events": events.name, "events_sha256": sha(events),
        })
        return digests

    try:
        # This driver requires Bazel 8.5.1 Bzlmod's standard execution root.
        # output_base avoids info execution_root's platform configuration while
        # retaining this exact wrapper, output base, cache and caller options.
        result = run([args.bazel, "info", *args.bazel_arg, "output_base"], capture=True)
        roots = result.stdout.splitlines()
        if len(roots) != 1 or not roots[0]:
            raise ValueError("expected one Bazel output base")
        output_base = Path(roots[0])
        execution_root = output_base / "execroot" / "_main"
        if not output_base.is_absolute() or not execution_root.is_dir():
            raise ValueError("missing Bazel 8.5.1 Bzlmod execution root")
        selected_script = query(SCRIPT_LABEL)
        if len(selected_script) != 1 or selected_script[0].resolve() != script:
            raise ValueError("run the selected @libteam owner script, not a local copy")
        baseline = build("baseline")
        # A reused lock may retain earlier lookups. Keep these as observed
        # evidence; the consumer's resolution receipt records effective options.
        lock = Path("MODULE.bazel.lock")
        if lock.is_file():
            registry_files = {url: value for url, value in
                              json.loads(lock.read_text()).get("registryFileHashes", {}).items()
                              if "/modules/libteam/" in url}
        if build("no-op") != baseline:
            raise ValueError("unchanged inputs changed owner outputs")
        try:
            config.write_bytes(original.replace(NEEDLE, EDIT))
            changed = build("config-edit")
            if changed.keys() != baseline.keys():
                raise ValueError("config edit changed the declared output set")
            utils = [path for path in baseline
                     if Path(path).name == "libteam_utils_runtime_rttar.tar"]
            if len(utils) != 1 or changed[utils[0]] == baseline[utils[0]]:
                raise ValueError("declared owner config edit did not invalidate the utilities TAR")
            stable = [path for path in baseline
                      if "libteam_utils_runtime" not in Path(path).name
                      and Path(path).name != "runtime_packages.json"]
            if len(stable) != 6 or any(changed[path] != baseline[path] for path in stable):
                raise ValueError("utilities config edit changed an unrelated owner output")
        finally:
            config.write_bytes(original)
        if build("restored") != baseline:
            raise ValueError("restored source did not reproduce the owner outputs")
        if sources != {name: sha(owner / name) for name in sources}:
            raise ValueError("owner source changed during the probe")
        status = "passed"
    finally:
        if not config.is_file() or config.read_bytes() != original:
            config.write_bytes(original)
        (args.output / "rebuild.json").write_text(json.dumps({
            "status": status,
            "scope": "Same-output-base output equality and config invalidation; "
                     "no zero-action, fresh-cache or remote-hit claim",
            "source_restored": config.read_bytes() == original,
            "owner_root": str(owner), "execution_root": str(execution_root),
            "owner_source_sha256": sources,
            "observed_registry_files": registry_files,
            "registry_evidence_scope": "Lock lookups may be historical; pair with the consumer's effective-registry receipt",
            "targets": targets, "bazel_arguments": args.bazel_arg,
            "commands": commands, "builds": records,
        }, indent=2) + "\n")


if __name__ == "__main__":
    main()
