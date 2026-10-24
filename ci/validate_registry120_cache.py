#!/usr/bin/env python3
"""Temporary native cache evidence for the immutable registry #120 candidate.

Reuse source a12bc826's declared-build-tools.yml cache replay contract, through
the registered module and the candidate's ordinary consumer configuration.
"""

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time


MODULE = "sonic-build-infra"
VERSION = "0.0.22-a12bc826d6f811a157db5c7c02a2fe033896cc14"
CANDIDATE = "01b7128186ec5fdb669477dc51fe4c1dc12dd4b5"
SOURCE = "a12bc826d6f811a157db5c7c02a2fe033896cc14"
KERNEL_POLICY = "--remote_download_regex=(^|.*/)tools/build_tools/kernel_runtime_(amd64|arm64)(/.*)?$"
TARGETS = [f"@{MODULE}//tools/build_tools:{name}_runtime_test"
           for name in ("configure", "foreign", "kernel")]


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def runtime_records(path):
    """The Bazel execution log contains concatenated JSON, not JSONL."""
    data = path.read_text()
    decoder = json.JSONDecoder()
    offset, records = 0, []
    while offset < len(data):
        while offset < len(data) and data[offset].isspace():
            offset += 1
        if offset == len(data):
            break
        record, offset = decoder.raw_decode(data, offset)
        if record.get("mnemonic") in ("PrepareBuildTools", "PrepareBuildToolsRootfs"):
            records.append({key: record.get(key) for key in (
                "mnemonic", "targetLabel", "listedOutputs", "runner", "cacheHit")})
    return records


def verify_cache(records, architecture):
    if {row["mnemonic"] for row in records} != {"PrepareBuildTools", "PrepareBuildToolsRootfs"}:
        raise ValueError("Replay must contain both runtime preparation action kinds")
    for runtime in ("configure", "foreign", "kernel"):
        suffix = f"//tools/build_tools:{runtime}_runtime_{architecture}"
        mnemonic = "PrepareBuildToolsRootfs" if runtime == "kernel" else "PrepareBuildTools"
        if not any(row["mnemonic"] == mnemonic and str(row["targetLabel"]).endswith(suffix)
                   for row in records):
            raise ValueError(f"Replay is missing the native {runtime} runtime action: {suffix}")
    if not all(row["cacheHit"] is True and row["runner"] == "disk cache hit" for row in records):
        raise ValueError("Every replay runtime action must be a real disk cache hit")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", required=True, type=Path)
    parser.add_argument("--architecture", required=True, choices=("amd64", "arm64"))
    parser.add_argument("--work-dir", required=True, type=Path)
    parser.add_argument("--artifacts", required=True, type=Path)
    parser.add_argument("--bazel", default="bazel")
    args = parser.parse_args()
    root, work, artifacts = args.registry.resolve(), args.work_dir.resolve(), args.artifacts.resolve()
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("candidate_registry_ci", root / "ci/registry_ci.py")
    ci = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ci)
    ci.require(ci.git(root, "rev-parse", "HEAD").strip() == CANDIDATE, "Wrong immutable registry candidate")
    ci.require(not ci.git(root, "status", "--porcelain").strip(), "Candidate checkout must be clean")
    ci.require(not work.exists(), "Cache validation work-dir must not exist")
    ci.require(not artifacts.exists(), "Cache validation artifacts must not exist")
    ci.require(not work.is_relative_to(root) and not artifacts.is_relative_to(root),
               "Work and evidence must be outside the immutable registry checkout")
    config = ci.validate_entry(root, MODULE, VERSION)
    ci.require(set(TARGETS) <= set(config["test_targets"]), "Replay targets must belong to the reviewed suite")
    ci.require(len(config["build_targets"]) == 29 and len(config["test_targets"]) == 26,
               "Candidate full-suite inventory changed")
    native = ci.verify_native(args.architecture)
    ci.require('VERSION_CODENAME=trixie' in Path('/etc/os-release').read_text(), "Debian Trixie is required")
    bazel_version = subprocess.check_output([args.bazel, "--version"], text=True).strip()
    ci.require(bazel_version == "bazel 8.5.1", "Bazel 8.5.1 is required")
    entry = ci.entry_directory(root, MODULE, VERSION)
    source = ci.read_json(entry / "source.json")
    ci.require(SOURCE in source["url"] and source["strip_prefix"] == f"sonic-build-infra-{SOURCE}",
               "Unexpected build-infra source revision")
    consumer = work / "consumer"
    consumer.mkdir(parents=True)
    artifacts.mkdir(parents=True)
    cache = work / "disk-cache"
    cache.mkdir()
    roots = {phase: work / f"bazel-{phase}" for phase in ("seed", "replay")}
    declarations = ['module(name = "registry_ci_consumer")']
    for dependency in [{"name": MODULE, "version": VERSION}, *config["consumer_deps"]]:
        declarations.append("bazel_dep(" + ", ".join(f"{key} = {json.dumps(value)}"
                            for key, value in dependency.items()) + ")")
    for dependency in config["consumer_deps"]:
        declarations.append(f'single_version_override(module_name = {json.dumps(dependency["name"])}, '
                            f'version = {json.dumps(dependency["version"])})')
    (consumer / "MODULE.bazel").write_text("\n\n".join(declarations) + "\n")
    (consumer / "BUILD.bazel").write_text("# Explicit external targets are built from this consumer.\n")
    (consumer / ".bazelversion").write_text("8.5.1\n")
    shutil.copy2(consumer / "MODULE.bazel", artifacts / "consumer.MODULE.bazel")
    shutil.copytree(entry, artifacts / "registry-entry")
    shutil.copy2('/etc/os-release', artifacts / 'os-release')
    resolution = [f"--registry={root.as_uri()}", "--registry=https://bcr.bazel.build/", "--lockfile_mode=update"]
    flags = [*resolution, f"--platforms={config['platforms'][args.architecture]}",
             f"--host_platform={config['host_platforms'][args.architecture]}", KERNEL_POLICY,
             f"--disk_cache={cache}", *config.get("build_flags", [])]
    receipt = dict(candidate=CANDIDATE, source=SOURCE, module=MODULE, version=VERSION, native=native,
                   bazel_version=bazel_version,
                   validator_head=os.environ.get("GITHUB_SHA"), github_run_id=os.environ.get("GITHUB_RUN_ID"),
                   consumer=str(consumer), disk_cache=str(cache), flags=flags, targets=TARGETS,
                   output_user_roots={phase: str(path) for phase, path in roots.items()},
                   result="incomplete", phases={})
    write_json(artifacts / "cache-validation.json", receipt)
    try:
        with ci.preserve_source_inputs(root, entry, artifacts, native):
            for phase, output_root in roots.items():
                phase_dir = artifacts / phase
                phase_dir.mkdir()
                ci.require(not output_root.exists(), f"{phase} output_user_root is not fresh")
                if phase == "replay":
                    ci.require(any(cache.iterdir()), "Seed disk cache is empty")
                prefix = [args.bazel, "--ignore_all_rc_files", f"--output_user_root={output_root}"]
                command = [*prefix, "test", *flags, "--nocache_test_results", "--test_output=errors",
                           f"--build_event_json_file={phase_dir / 'test-events.jsonl'}",
                           f"--execution_log_json_file={phase_dir / 'spawns.json'}", "--execution_log_sort=false",
                           *TARGETS]
                record = dict(command=command, output_root_was_absent=True, result="incomplete")
                receipt["phases"][phase] = record
                rows = []
                started = time.monotonic()
                try:
                    ci.run_logged(command, consumer, phase_dir / "test.log")
                    ci.verify_tests(phase_dir / "test-events.jsonl", TARGETS)
                    output_base = Path(subprocess.check_output(
                        [*prefix, "info", *resolution, "output_base"], cwd=consumer, text=True).strip())
                    record["output_base"] = str(output_base)
                    fetched = ci.fetched_modules(output_base, MODULE)
                    ci.require(len(fetched) == 1, "Expected one fetched build-infra module")
                    canonical = (entry / "MODULE.bazel").read_bytes()
                    ci.require(fetched[0].read_bytes() == canonical, "Fetched MODULE differs from registry")
                    record["fetched_module_matches_registry"] = True
                    record["fetched_module_sha256"] = hashlib.sha256(canonical).hexdigest()
                    shutil.copy2(fetched[0], phase_dir / "fetched.MODULE.bazel")
                    ci.run_logged([*prefix, "mod", "show_repo", *resolution, f"@{MODULE}"],
                                  consumer, phase_dir / "source-repository.log")
                    repository = (phase_dir / "source-repository.log").read_text()
                    ci.require(source["url"] in repository and source["integrity"] in repository,
                               "Fetched repository must identify the exact source archive and integrity")
                finally:
                    record["elapsed_seconds"] = round(time.monotonic() - started, 3)
                    if (phase_dir / "spawns.json").exists():
                        rows = runtime_records(phase_dir / "spawns.json")
                        write_json(phase_dir / "runtime-actions.json", rows)
                    if (consumer / "MODULE.bazel.lock").exists():
                        shutil.copy2(consumer / "MODULE.bazel.lock", phase_dir / "MODULE.bazel.lock")
                    if (consumer / "bazel-testlogs").exists():
                        shutil.copytree(consumer / "bazel-testlogs", phase_dir / "testlogs", dirs_exist_ok=True)
                    subprocess.run([*prefix, "shutdown"], cwd=consumer, check=False)
                if phase == "replay":
                    write_json(artifacts / "cache-reuse.json", rows)
                    ci.require((phase_dir / "spawns.json").is_file(), "Replay execution log is missing")
                    verify_cache(rows, args.architecture)
                    ci.require(record["output_base"] != receipt["phases"]["seed"]["output_base"],
                               "Replay output base must differ from seed")
                record["result"] = "passed"
            ci.require(not ci.git(root, "status", "--porcelain").strip(), "Immutable candidate was modified")
            receipt["result"] = "passed"
    except Exception as error:
        receipt["result"] = "failed"
        receipt["error"] = f"{type(error).__name__}: {error}"
        if receipt["phases"]:
            receipt["phases"][next(reversed(receipt["phases"]))]["result"] = "failed"
        raise
    finally:
        write_json(artifacts / "cache-validation.json", receipt)


if __name__ == "__main__":
    main()
