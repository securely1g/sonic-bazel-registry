#!/usr/bin/env python3
"""Validate registry entries and test them from an independent Bazel consumer."""

from __future__ import annotations

import argparse
import ast
import base64
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import subprocess
import sys
import tokenize
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
RUNNERS = {"amd64": "ubuntu-24.04", "arm64": "ubuntu-24.04-arm"}
NAME = re.compile(r"[a-z][a-z0-9._-]*\Z")
VERSION = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]*\Z")
LABEL = re.compile(r"@[a-z][a-z0-9._-]*//[A-Za-z0-9_./+-]*:[A-Za-z0-9_./+-]+\Z")


class RegistryError(ValueError):
    """A registry entry or required validation result is invalid."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RegistryError(message)


def read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text())
    except (OSError, ValueError) as error:
        raise RegistryError(f"Cannot read {path}: {error}") from error
    require(isinstance(value, dict), f"{path}: expected a JSON object")
    return value


def parse_module_identity(text: str) -> tuple[str, str]:
    """Read a literal, top-level module() call without executing Starlark."""
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(text).readline))
    except (tokenize.TokenError, IndentationError) as error:
        raise RegistryError(f"Cannot tokenize MODULE.bazel: {error}") from error
    calls = []
    depth = 0
    for index, token in enumerate(tokens):
        if token.string == "module" and token.type == tokenize.NAME and depth == 0:
            following = tokens[index + 1]
            if following.string == "(":
                nesting = 0
                for end in range(index + 1, len(tokens)):
                    if tokens[end].string == "(":
                        nesting += 1
                    elif tokens[end].string == ")":
                        nesting -= 1
                        if nesting == 0:
                            call = tokenize.untokenize(tokens[index:end + 1]).strip()
                            try:
                                calls.append(ast.parse(call, mode="eval").body)
                            except SyntaxError as error:
                                raise RegistryError("Unsupported module() declaration") from error
                            break
        if token.type == tokenize.OP:
            if token.string in ("(", "[", "{"):
                depth += 1
            elif token.string in (")", "]", "}"):
                depth -= 1
    require(len(calls) == 1, "MODULE.bazel must contain exactly one module() declaration")
    call = calls[0]
    require(isinstance(call, ast.Call) and not call.args, "module() must use literal named arguments")
    values = {}
    for keyword in call.keywords:
        if keyword.arg in ("name", "version"):
            require(keyword.arg not in values, f"Duplicate module {keyword.arg}")
            require(isinstance(keyword.value, ast.Constant) and isinstance(keyword.value.value, str),
                    f"module {keyword.arg} must be a literal string")
            values[keyword.arg] = keyword.value.value
    require(set(values) == {"name", "version"}, "module() needs literal name and version")
    return values["name"], values["version"]


def sri(integrity: str, data: bytes | None = None) -> None:
    require(isinstance(integrity, str), "integrity must be a string")
    match = re.fullmatch(r"(sha256|sha384|sha512)-([A-Za-z0-9+/]+={0,2})", integrity)
    require(match is not None, f"Unsupported integrity: {integrity}")
    algorithm, encoded = match.groups()
    try:
        digest = base64.b64decode(encoded, validate=True)
    except ValueError as error:
        raise RegistryError(f"Invalid integrity: {integrity}") from error
    require(len(digest) == hashlib.new(algorithm).digest_size, "Incorrect integrity digest length")
    if data is not None:
        require(hashlib.new(algorithm, data).digest() == digest, "Integrity checksum mismatch")


def local_input(directory: Path, name: str) -> Path:
    require(isinstance(name, str), "Registry input name must be a string")
    path = PurePosixPath(name)
    require(bool(name) and not path.is_absolute() and all(part not in ("..", ".") for part in path.parts),
            f"Unsafe registry input path: {name}")
    require("\\" not in name and "//" not in name, f"Unsafe registry input path: {name}")
    result = directory / name
    require(result.is_file() and not result.is_symlink(), f"Missing regular input: {result}")
    require(result.resolve().is_relative_to(directory.resolve()), f"Input escapes its directory: {result}")
    return result


def validate_entry(root: Path, module: str, version: str) -> dict:
    require(NAME.fullmatch(module) is not None, f"Invalid module name: {module}")
    require(VERSION.fullmatch(version) is not None, f"Invalid module version: {version}")
    entry = root / "modules" / module / version
    require(entry.is_dir() and not entry.is_symlink(), f"Missing version directory: {entry}")
    metadata = read_json(entry.parent / "metadata.json")
    versions = metadata.get("versions")
    require(isinstance(versions, list) and all(isinstance(v, str) for v in versions), "metadata needs versions")
    require(len(versions) == len(set(versions)) and version in versions, "metadata version list is inconsistent")
    try:
        identity = parse_module_identity((entry / "MODULE.bazel").read_text())
    except OSError as error:
        raise RegistryError(f"Cannot read registry MODULE.bazel: {error}") from error
    require(identity == (module, version), f"Registry module identity {identity} disagrees with directory")
    source = read_json(entry / "source.json")
    require(source.get("type", "archive") == "archive", "Only archive registry entries are supported")
    url = source.get("url")
    require(isinstance(url, str) and urlparse(url).scheme == "https" and bool(urlparse(url).netloc),
            "Source archive must have an HTTPS URL")
    sri(source.get("integrity"))
    require(type(source.get("patch_strip", 0)) is int and source.get("patch_strip", 0) >= 0,
            "patch_strip must be a nonnegative integer")
    for key, folder in (("patches", "patches"), ("overlay", "overlay")):
        inputs = source.get(key, {})
        require(isinstance(inputs, dict), f"source.{key} must be an object")
        for name, integrity in inputs.items():
            path = local_input(entry / folder, name)
            try:
                sri(integrity, path.read_bytes())
            except RegistryError as error:
                raise RegistryError(f"{path}: {error}") from error
        if (entry / folder).exists():
            actual = {path.relative_to(entry / folder).as_posix()
                      for path in (entry / folder).rglob("*") if path.is_file()}
            require(actual == set(inputs), f"Unlisted or missing {folder} files: {actual ^ set(inputs)}")

    config = read_json(entry / "presubmit.json")
    required = {"architectures", "consumer_deps", "platforms", "build_targets", "test_targets"}
    require(required <= set(config) <= required | {"build_flags"},
            f"presubmit.json requires {sorted(required)} and optionally build_flags")
    architectures = config["architectures"]
    require(isinstance(architectures, list) and bool(architectures)
            and all(isinstance(a, str) and a in RUNNERS for a in architectures)
            and len(set(architectures)) == len(architectures),
            "architectures must list supported, unique native architectures")
    platforms = config["platforms"]
    require(isinstance(platforms, dict) and set(platforms) == set(architectures)
            and all(isinstance(label, str) and LABEL.fullmatch(label) for label in platforms.values()),
            "platforms must map each architecture to an explicit external target")
    aliases = {module}
    names = {module}
    require(isinstance(config["consumer_deps"], list), "consumer_deps must be a list")
    for dependency in config["consumer_deps"]:
        require(isinstance(dependency, dict) and set(dependency) in ({"name", "version"}, {"name", "version", "repo_name"}),
                "consumer_deps require name/version and optional repo_name")
        name, dep_version = dependency["name"], dependency["version"]
        alias = dependency.get("repo_name", name)
        require(isinstance(name, str) and NAME.fullmatch(name) is not None and name not in names,
                "Invalid or duplicate consumer dependency")
        require(isinstance(dep_version, str) and VERSION.fullmatch(dep_version) is not None,
                "Invalid consumer dependency version")
        require(isinstance(alias, str) and NAME.fullmatch(alias) is not None and alias not in aliases,
                "Invalid or duplicate consumer repository name")
        names.add(name)
        aliases.add(alias)
    for field in ("build_targets", "test_targets"):
        labels = config[field]
        require(isinstance(labels, list) and bool(labels) and all(isinstance(label, str) for label in labels),
                f"{field} must be a nonempty list")
        require(len(set(labels)) == len(labels), f"{field} must have unique targets")
        for label in labels:
            require(LABEL.fullmatch(label) is not None and label.startswith(f"@{module}//")
                    and label.rsplit(":", 1)[1] not in ("all", "all-targets"),
                    f"{field} requires explicit targets in @{module}: {label}")
    build_flags = config.get("build_flags", [])
    require(isinstance(build_flags, list), "build_flags must be a list")
    settings = set()
    for flag in build_flags:
        require(isinstance(flag, str) and "=" in flag and not any(c.isspace() for c in flag),
                "build_flags requires module-qualified Starlark settings with explicit values")
        setting, value = flag.split("=", 1)
        require(setting.startswith(f"--@{module}//") and LABEL.fullmatch(setting[2:]) is not None
                and bool(value) and setting not in settings,
                "build_flags must set unique Starlark settings in the module under test")
        settings.add(setting)
    return config


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True)


def plan(root: Path, base: str | None, head: str | None, all_versions: bool = False) -> dict:
    selected = set()
    if all_versions:
        selected.update((path.parent.parent.name, path.parent.name)
                        for path in (root / "modules").glob("*/*/presubmit.json"))
    else:
        require(bool(base) and bool(head), "plan requires --base/--head or --all")
        require(re.fullmatch(r"[0-9a-fA-F]{40,64}", base) is not None
                and re.fullmatch(r"[0-9a-fA-F]{40,64}", head) is not None,
                "base and head must be full commit SHAs")
        require(git(root, "rev-parse", "HEAD").strip() == head, "Checkout HEAD differs from planned head")
        changed = git(root, "diff", "--name-only", "--no-renames", "-z", base, head).split("\0")
        for name in filter(None, changed):
            parts = PurePosixPath(name).parts
            if parts[0] in ("ci", ".github") or name == "bazel_registry.json":
                selected.update((path.parent.parent.name, path.parent.name)
                                for path in (root / "modules").glob("*/*/presubmit.json"))
            elif parts[0] == "modules":
                require(len(parts) >= 3, f"Unsupported module path: {name}")
                module = parts[1]
                if len(parts) == 3 and parts[2] == "README.md":
                    # Module documentation does not name a version or require a
                    # manifest for every unchanged historical release.
                    continue
                if parts[2] == "metadata.json":
                    metadata = read_json(root / "modules" / module / "metadata.json")
                    versions = metadata.get("versions")
                    require(isinstance(versions, list) and bool(versions)
                            and all(isinstance(v, str) for v in versions),
                            "Changed module metadata needs versions")
                    require(len(versions) == len(set(versions)), "Metadata contains duplicate versions")
                    directories = {p.name for p in (root / "modules" / module).iterdir() if p.is_dir()}
                    require(set(versions) == directories, f"{module}: metadata and version directories differ")
                    previous = subprocess.run(
                        ["git", "-C", str(root), "show", f"{base}:modules/{module}/metadata.json"],
                        text=True, capture_output=True,
                    )
                    relevant = versions
                    if previous.returncode == 0:
                        old = json.loads(previous.stdout)
                        old_versions = old.get("versions", [])
                        added = set(versions) - set(old_versions)
                        old_fields = {key: value for key, value in old.items() if key != "versions"}
                        new_fields = {key: value for key, value in metadata.items() if key != "versions"}
                        # A release append does not require retrofitting CI to every
                        # historical version. Other metadata changes cover them all.
                        if added and old_fields == new_fields and [v for v in versions if v in old_versions] == old_versions:
                            relevant = [v for v in versions if v in added]
                    selected.update((module, version) for version in relevant)
                else:
                    require(len(parts) >= 4, f"Unsupported version path: {name}")
                    selected.add((module, parts[2]))
    include = []
    for module, version in sorted(selected):
        config = validate_entry(root, module, version)
        for architecture in config["architectures"]:
            include.append({"module": module, "version": version, "architecture": architecture,
                            "runner": RUNNERS[architecture]})
    return {"include": include}


def normalized_label(label: str) -> str:
    """BEP uses canonical repository names, whereas manifests use apparent names."""
    if label.startswith("@@"):
        repository, target = label[2:].split("//", 1)
        return "@" + repository.split("+", 1)[0] + "//" + target
    return label


def verify_tests(bep_path: Path, labels: list[str]) -> None:
    summaries = {}
    executed = set()
    for line in bep_path.read_text().splitlines():
        event = json.loads(line)
        identifier = event.get("id", {})
        if "testSummary" in identifier:
            label = normalized_label(identifier["testSummary"]["label"])
            summary = event.get("testSummary", {})
            require(label not in summaries, f"Multiple test configurations for {label}")
            summaries[label] = summary
        if "testResult" in identifier:
            label = normalized_label(identifier["testResult"]["label"])
            result = event.get("testResult", {})
            if label in labels:
                require(result.get("status") == "PASSED", f"{label}: a test attempt did not pass")
                require(not result.get("cachedLocally", False)
                        and not result.get("executionInfo", {}).get("cachedRemotely", False),
                        f"{label}: test result was cached")
                executed.add(label)
    for label in labels:
        require(label in summaries and label in executed, f"Required test did not execute: {label}")
        summary = summaries[label]
        require(summary.get("overallStatus") == "PASSED", f"{label}: required test did not pass")
        require(summary.get("totalRunCount", 0) > 0 and summary.get("totalNumCached", 0) == 0,
                f"{label}: required test did not run uncached")


def run_logged(command: list[str], cwd: Path, log: Path) -> None:
    print(f"Running Bazel validation; log: {log}", flush=True)
    with log.open("w") as output:
        result = subprocess.run(command, cwd=cwd, stdout=output, stderr=subprocess.STDOUT)
    if result.returncode:
        print(log.read_text()[-16000:], file=sys.stderr)
        raise RegistryError(f"Command failed with status {result.returncode}; see {log}")


def run(root: Path, module: str, version: str, architecture: str,
        work_dir: Path, artifacts: Path, bazel: str = "bazel") -> None:
    config = validate_entry(root, module, version)
    require(architecture in config["architectures"], "Architecture is not configured for this version")
    require(platform.system() == "Linux" and platform.machine() == {"amd64": "x86_64", "arm64": "aarch64"}[architecture],
            "Validation must run on a native Linux host of the requested architecture")
    work_dir, artifacts = work_dir.resolve(), artifacts.resolve()
    require(not work_dir.exists() or not any(work_dir.iterdir()), "work-dir must be fresh and empty")
    require(not artifacts.is_relative_to(work_dir), "artifacts must be outside work-dir")
    consumer = work_dir / "consumer"
    consumer.mkdir(parents=True)
    artifacts.mkdir(parents=True, exist_ok=True)
    declarations = ['module(name = "registry_ci_consumer")']
    for dependency in [{"name": module, "version": version}, *config["consumer_deps"]]:
        declarations.append("bazel_dep(" + ", ".join(f"{key} = {json.dumps(value)}"
                                                   for key, value in dependency.items()) + ")")
    (consumer / "MODULE.bazel").write_text("\n\n".join(declarations) + "\n")
    (consumer / "BUILD.bazel").write_text("# Explicit external targets are built from this consumer.\n")
    (consumer / ".bazelversion").write_text("8.5.1\n")
    shutil.copy2(consumer / "MODULE.bazel", artifacts / "consumer.MODULE.bazel")
    prefix = [bazel, "--ignore_all_rc_files", f"--output_user_root={work_dir / 'bazel'}"]
    flags = [f"--registry={root.resolve().as_uri()}", "--registry=https://bcr.bazel.build/",
             f"--platforms={config['platforms'][architecture]}", "--lockfile_mode=off",
             *config.get("build_flags", [])]
    try:
        run_logged([*prefix, "build", *flags, f"--build_event_json_file={artifacts / 'build-events.jsonl'}",
                    *config["build_targets"]], consumer, artifacts / "build.log")
        run_logged([*prefix, "test", *flags, "--nocache_test_results", "--test_output=errors",
                    f"--build_event_json_file={artifacts / 'test-events.jsonl'}", *config["test_targets"]],
                   consumer, artifacts / "test.log")
        verify_tests(artifacts / "test-events.jsonl", config["test_targets"])
        output_base = Path(subprocess.check_output([*prefix, "info", *flags, "output_base"],
                                                  cwd=consumer, text=True).strip())
        fetched = list((output_base / "external").glob(f"{module}+*/MODULE.bazel"))
        require(len(fetched) == 1, f"Expected one fetched repository for {module}, found {len(fetched)}")
        registry_module = root / "modules" / module / version / "MODULE.bazel"
        require(parse_module_identity(fetched[0].read_text()) == (module, version),
                "Fetched source module name/version differs from requested registry entry")
        require(fetched[0].read_bytes() == registry_module.read_bytes(),
                "Fetched MODULE.bazel differs from registry MODULE.bazel")
        shutil.copy2(fetched[0], artifacts / "fetched.MODULE.bazel")
        (artifacts / "validation.json").write_text(json.dumps({
            "module": module, "version": version, "architecture": architecture,
            "build_targets": config["build_targets"], "passed_tests": config["test_targets"],
            "build_flags": config.get("build_flags", []),
            "fetched_module_matches_registry": True,
        }, indent=2) + "\n")
    finally:
        testlogs = consumer / "bazel-testlogs"
        if testlogs.exists():
            shutil.copytree(testlogs, artifacts / "testlogs", dirs_exist_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    planner = subparsers.add_parser("plan")
    planner.add_argument("--base")
    planner.add_argument("--head")
    planner.add_argument("--all", action="store_true", dest="all_versions")
    planner.add_argument("--output", required=True, type=Path)
    runner = subparsers.add_parser("run")
    runner.add_argument("--module", required=True)
    runner.add_argument("--version", required=True)
    runner.add_argument("--architecture", required=True, choices=RUNNERS)
    runner.add_argument("--work-dir", required=True, type=Path)
    runner.add_argument("--artifacts", required=True, type=Path)
    runner.add_argument("--bazel", default="bazel")
    args = parser.parse_args()
    try:
        if args.command == "plan":
            result = plan(ROOT, args.base, args.head, args.all_versions)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(result, indent=2) + "\n")
            print(json.dumps(result, separators=(",", ":")))
            print(f"Selected {len(result['include'])} native validation jobs", file=sys.stderr)
        else:
            run(ROOT, args.module, args.version, args.architecture, args.work_dir, args.artifacts, args.bazel)
    except (RegistryError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Registry CI failed: {error}\n")


if __name__ == "__main__":
    main()
