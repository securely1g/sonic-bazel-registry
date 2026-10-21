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
import tarfile
import tempfile
import tokenize
from urllib.parse import unquote, urlparse
from urllib.request import urlopen


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
        # Module extensions may also expose a method named module(). Only the
        # bare module() declaration identifies this registry entry.
        attribute = index > 0 and tokens[index - 1].string == "."
        if token.string == "module" and token.type == tokenize.NAME and depth == 0 and not attribute:
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


def entry_directory(root: Path, module: str, version: str) -> Path:
    require(NAME.fullmatch(module) is not None, f"Invalid module name: {module}")
    require(VERSION.fullmatch(version) is not None, f"Invalid module version: {version}")
    entry = root / "modules" / module / version
    require(entry.is_dir() and not entry.is_symlink(), f"Missing version directory: {entry}")
    require(entry.resolve().is_relative_to(root.resolve()), f"Version directory escapes registry: {entry}")
    return entry


def module_overlay_bytes(entry: Path, module: str, version: str) -> bytes:
    canonical = local_input(entry, "MODULE.bazel").read_bytes()
    require(parse_module_identity(canonical.decode("utf-8")) == (module, version),
            "Registry module identity disagrees with directory")
    header = ("# AUTO-GENERATED. DO NOT EDIT MANUALLY.\n"
              "# Source: ../MODULE.bazel\n"
              f"# Generator: python3 ci/registry_ci.py sync-module --module {module} --version {version}\n\n")
    return header.encode("utf-8") + canonical


def sync_module(root: Path, module: str, version: str, check: bool = False) -> None:
    """Generate only the opted-in MODULE overlay and its source.json checksum."""
    entry = entry_directory(root, module, version)
    config = read_json(local_input(entry, "presubmit.json"))
    require(config.get("generated_module_overlay") is True,
            "sync-module requires generated_module_overlay: true in presubmit.json")
    expected = module_overlay_bytes(entry, module, version)
    source_path = local_input(entry, "source.json")
    source = read_json(source_path)
    overlays = source.get("overlay", {})
    require(isinstance(overlays, dict), "source.overlay must be an object")
    directory = entry / "overlay"
    require(not directory.is_symlink() and (not directory.exists() or directory.is_dir()),
            f"Overlay directory must be a real directory: {directory}")
    output = directory / "MODULE.bazel"
    require(not output.is_symlink(), f"Generated overlay must not be a symlink: {output}")
    if output.exists():
        local_input(directory, "MODULE.bazel")
    integrity = "sha256-" + base64.b64encode(hashlib.sha256(expected).digest()).decode("ascii")
    if check:
        command = f"python3 ci/registry_ci.py sync-module --module {module} --version {version}"
        try:
            require(local_input(directory, "MODULE.bazel").read_bytes() == expected,
                    "Generated MODULE overlay differs from canonical MODULE.bazel")
            sri(overlays.get("MODULE.bazel"), expected)
            require(overlays["MODULE.bazel"] == integrity, "Generated MODULE overlay checksum is stale")
        except RegistryError as error:
            raise RegistryError(f"{error}; run: {command}") from error
        return
    # Refuse shared inodes as well as symlinks before either write. The canonical
    # MODULE and unrelated files must never change through an output alias.
    require(source_path.stat().st_nlink == 1 and (not output.exists() or output.stat().st_nlink == 1),
            "Generated overlay and source.json must not be hard-linked")
    if not output.exists() or output.read_bytes() != expected:
        directory.mkdir(exist_ok=True)
        output.write_bytes(expected)
    if overlays.get("MODULE.bazel") != integrity:
        source.setdefault("overlay", {})["MODULE.bazel"] = integrity
        source_path.write_text(json.dumps(source, indent=2) + "\n")


def validate_entry(root: Path, module: str, version: str) -> dict:
    entry = entry_directory(root, module, version)
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
    require(required <= set(config) <= required | {
        "build_flags", "rust_preparation", "go_sdk", "rust_toolchain", "generated_module_overlay",
    }, f"presubmit.json requires {sorted(required)} and optionally "
       "build_flags/rust_preparation/go_sdk/rust_toolchain/generated_module_overlay")
    if "generated_module_overlay" in config:
        require(config["generated_module_overlay"] is True, "generated_module_overlay must be true when present")
        sync_module(root, module, version, check=True)
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
    if "go_sdk" in config:
        sdk = config["go_sdk"]
        require(isinstance(sdk, dict) and set(sdk) == {"version"},
                "go_sdk requires only an exact version")
        require(isinstance(sdk["version"], str)
                and re.fullmatch(r"1\.[0-9]+\.[0-9]+", sdk["version"]) is not None,
                "go_sdk version must be an exact stable Go release such as 1.25.0")
        require("rules_go" in names,
                "go_sdk requires rules_go as the tested module or a declared consumer dependency")
    if "rust_toolchain" in config:
        toolchain = config["rust_toolchain"]
        require(isinstance(toolchain, dict)
                and {"version"} <= set(toolchain) <= {"version", "mangled_allocator_libraries", "bindgen"},
                "rust_toolchain requires version and optionally mangled_allocator_libraries/bindgen")
        require(isinstance(toolchain["version"], str)
                and re.fullmatch(r"1\.[0-9]+\.[0-9]+", toolchain["version"]) is not None,
                "rust_toolchain version must be an exact stable Rust release such as 1.90.0")
        require("rules_rs" in names,
                "rust_toolchain requires rules_rs as the tested module or a declared consumer dependency")
        for option in ("mangled_allocator_libraries", "bindgen"):
            require(type(toolchain.get(option, False)) is bool, f"rust_toolchain {option} must be a boolean")
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
    if "rust_preparation" in config:
        preparation = config["rust_preparation"]
        require(isinstance(preparation, dict) and set(preparation) == {
            "module", "repo_name", "helper_revision", "helper_sha256",
        }, "rust_preparation requires module, repo_name, helper_revision and helper_sha256")
        dependencies = {module: module, **{
            dependency["name"]: dependency.get("repo_name", dependency["name"])
            for dependency in config["consumer_deps"]
        }}
        require(isinstance(preparation["module"], str)
                and dependencies.get(preparation["module"]) == preparation["repo_name"],
                "Rust preparation must select the tested module or a declared consumer dependency")
        require(isinstance(preparation["helper_revision"], str)
                and re.fullmatch(r"[0-9a-f]{40}", preparation["helper_revision"]) is not None,
                "Rust preparation helper_revision must be a full commit SHA")
        require(isinstance(preparation["helper_sha256"], str)
                and re.fullmatch(r"[0-9a-f]{64}", preparation["helper_sha256"]) is not None,
                "Rust preparation helper_sha256 must be a SHA256 digest")
    return config


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True)


def release_key(version: str) -> tuple[tuple[int, ...], int, int]:
    """Order registry releases and patches without treating Git hashes as dates."""
    match = re.fullmatch(r"([0-9]+(?:\.[0-9]+)*)(.*)", version)
    require(match is not None, f"Cannot select latest registry version: {version}")
    release, suffix = match.groups()
    numbers = tuple(int(part) for part in release.split("."))
    # Equivalent numeric releases must still use registration order for snapshots.
    while len(numbers) > 1 and numbers[-1] == 0:
        numbers = numbers[:-1]
    patch = re.fullmatch(r"([.-])sonic\.([0-9]+)", suffix)
    if patch:
        return numbers, int(patch[2]), int(patch[1] == ".")
    require(suffix in ("", ".sonic-buildimage", ".sonic-patched")
            or re.fullmatch(r"(?:-|\.commit-)[0-9a-f]{7,40}", suffix) is not None,
            f"Unsupported registry version for latest selection: {version}")
    return numbers, 0, 0


def latest_presubmits(root: Path) -> set[tuple[str, str]]:
    """Select the newest non-yanked release of each module already covered by CI."""
    modules = {path.parent.parent for path in (root / "modules").glob("*/*/presubmit.json")}
    selected = set()
    for directory in sorted(modules):
        metadata = read_json(directory / "metadata.json")
        versions = metadata.get("versions")
        require(isinstance(versions, list) and bool(versions)
                and all(isinstance(v, str) and VERSION.fullmatch(v) for v in versions),
                f"{directory.name}: metadata needs valid versions")
        require(len(versions) == len(set(versions)), f"{directory.name}: duplicate metadata versions")
        directories = {path.name for path in directory.iterdir() if path.is_dir()}
        require(set(versions) == directories, f"{directory.name}: metadata and version directories differ")
        yanked = metadata.get("yanked_versions", {})
        require(isinstance(yanked, dict) and set(yanked) <= set(versions)
                and all(isinstance(reason, str) for reason in yanked.values()),
                f"{directory.name}: invalid yanked_versions metadata")
        eligible = [(release_key(version), index, version)
                    for index, version in enumerate(versions) if version not in yanked]
        if not eligible:
            print(f"Skipping {directory.name}: all versions are yanked", file=sys.stderr)
            continue
        # Numeric release/patch first; metadata append order breaks snapshot ties.
        version = max(eligible)[2]
        require((directory / version / "presubmit.json").is_file(),
                f"{directory.name}: latest version {version} needs presubmit.json")
        selected.add((directory.name, version))
    return selected


def plan(root: Path, base: str | None, head: str | None, all_versions: bool = False,
         latest_versions: bool = False) -> dict:
    require(not (all_versions and latest_versions), "Choose either --all or --latest")
    require(not ((all_versions or latest_versions) and (base or head)),
            "Do not combine --all/--latest with --base/--head")
    selected = set()
    if all_versions:
        selected.update((path.parent.parent.name, path.parent.name)
                        for path in (root / "modules").glob("*/*/presubmit.json"))
    elif latest_versions:
        selected.update(latest_presubmits(root))
    else:
        require(bool(base) and bool(head), "plan requires --base/--head, --latest or --all")
        require(re.fullmatch(r"[0-9a-fA-F]{40,64}", base) is not None
                and re.fullmatch(r"[0-9a-fA-F]{40,64}", head) is not None,
                "base and head must be full commit SHAs")
        require(git(root, "rev-parse", "HEAD").strip() == head, "Checkout HEAD differs from planned head")
        # A PR compares its own changes with the common ancestor. Releases
        # added only to its target branch are not deletions from this checkout.
        comparison_base = git(root, "merge-base", base, head).strip()
        changed = git(root, "diff", "--name-only", "--no-renames", "-z", comparison_base, head).split("\0")
        ci_changed = False
        for name in filter(None, changed):
            parts = PurePosixPath(name).parts
            if parts[0] in ("ci", ".github") or name == "bazel_registry.json":
                ci_changed = True
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
                        ["git", "-C", str(root), "show", f"{comparison_base}:modules/{module}/metadata.json"],
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
        if ci_changed:
            selected.update(latest_presubmits(root))
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


def query_output_trees(prefix: list[str], flags: list[str], labels: list[str],
                       consumer: Path, artifacts: Path) -> dict[str, list[str]]:
    """Recover declared directory boundaries that the BEP expands into files."""
    manifest = artifacts / "declared-output-trees.jsonl"
    log = artifacts / "declared-output-trees.log"
    with manifest.open("w") as output, log.open("w") as errors:
        for label in labels:
            # cquery resolves target.label through aliases, while BEP completion
            # records retain the requested alias. Query separately so every
            # directory remains associated with its exact requested target.
            expression = ('json.encode({"label": ' + json.dumps(label) + ', '
                          '"resolved_label": str(target.label), '
                          '"trees": [f.path for f in target.files.to_list() if f.is_directory]})')
            result = subprocess.run(
                [*prefix, "cquery", *flags, "--output=starlark", f"--starlark:expr={expression}",
                 label], cwd=consumer, stdout=output, stderr=errors)
            require(result.returncode == 0, f"Declared output query failed for {label}; see {log}")
    trees = {}
    for line in manifest.read_text().splitlines():
        value = json.loads(line)
        require(isinstance(value, dict) and isinstance(value.get("label"), str)
                and isinstance(value.get("trees"), list), "Invalid declared output query record")
        label = normalized_label(value["label"])
        require(label in labels and label not in trees, f"Unexpected or repeated output query target: {label}")
        paths = value["trees"]
        for path in paths:
            require(isinstance(path, str), "Declared tree path must be a string")
            relative = PurePosixPath(path)
            require(bool(relative.parts) and relative.parts[0] == "bazel-out"
                    and ".." not in relative.parts and "\\" not in path,
                    f"Unsafe declared tree path: {path}")
        require(len(paths) == len(set(paths)), f"Repeated declared directory for {label}")
        trees[label] = paths
    require(set(trees) == set(labels), "Declared output query omitted required targets")
    return trees


def collect_outputs(bep_path: Path, labels: list[str], work_dir: Path, artifacts: Path,
                    declared_trees: dict[str, list[str]] | None = None,
                    execution_root: Path | None = None) -> None:
    """Retain declared default outputs, including tree artifacts, from a build BEP."""
    sets, completed = {}, {}
    for line in bep_path.read_text().splitlines():
        event = json.loads(line)
        identifier = event.get("id", {})
        if "namedSet" in identifier:
            sets[identifier["namedSet"]["id"]] = event.get("namedSetOfFiles", {})
        if "targetCompleted" in identifier:
            label = normalized_label(identifier["targetCompleted"]["label"])
            if label in labels:
                require(label not in completed, f"Multiple build configurations for {label}")
                completed[label] = event.get("completed", {})

    work_dir = work_dir.resolve()
    declared_trees = declared_trees or {}
    require(not declared_trees or set(declared_trees) == set(labels),
            "Declared directory manifest must cover exactly the requested targets")
    if execution_root is not None:
        execution_root = execution_root.resolve()
        require(execution_root.is_relative_to(work_dir), "Execution root escapes work-dir")
    outputs = artifacts / "outputs"
    require(not outputs.exists(), f"Output destination already exists: {outputs}")
    outputs.mkdir(parents=True)
    retained = {}

    def archive_tree(source: Path, relative: PurePosixPath) -> dict:
        # GitHub artifacts reject ':' and fold case. Put POSIX tree contents in
        # a TAR whose upload name depends only on the declared output path.
        key = hashlib.sha256(relative.as_posix().encode()).hexdigest()
        destination = outputs / "trees" / (key + ".tar")
        destination.parent.mkdir(parents=True, exist_ok=True)

        def normalize(member: tarfile.TarInfo) -> tarfile.TarInfo:
            member.uid = member.gid = member.mtime = 0
            member.uname = member.gname = ""
            return member

        def add(tree: tarfile.TarFile, path: Path, name: PurePosixPath,
                ancestors: frozenset = frozenset()) -> None:
            resolved = path.resolve()
            require(resolved.is_relative_to(work_dir), f"Build output escapes work-dir: {resolved}")
            require(resolved.is_file() or resolved.is_dir(), f"Missing regular build output: {resolved}")
            if resolved.is_dir():
                require(resolved not in ancestors, f"Build output directory cycle: {resolved}")
            # Preserve portable links inside this tree. Links into other build
            # outputs are materialized, as before, so they remain usable alone.
            if path.is_symlink() and path.is_relative_to(source):
                link = path.readlink()
                # A link copied through a materialized directory may have a
                # different parent in the archive. Preserve it only when both
                # its location and its relative target retain their meaning.
                # Never retain a link that leaves the tree and then re-enters
                # it: the parent directories are absent in a standalone TAR.
                lexical_target = path.parent
                stays_inside = not link.is_absolute()
                for part in link.parts:
                    lexical_target = lexical_target.parent if part == ".." else lexical_target / part
                    if not lexical_target.is_relative_to(source):
                        stays_inside = False
                        break
                if (stays_inside and name == relative / path.relative_to(source)
                        and resolved.is_relative_to(source) and lexical_target.resolve() == resolved):
                    tree.add(path, arcname=name.as_posix(), recursive=False, filter=normalize)
                    return
            tree.add(resolved, arcname=name.as_posix(), recursive=False, filter=normalize)
            if resolved.is_dir():
                for child in sorted(resolved.iterdir()):
                    add(tree, child, name / child.name, ancestors | {resolved})

        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=destination.parent, suffix=".tmp", delete=False) as stream:
                temporary = Path(stream.name)
                with tarfile.open(fileobj=stream, mode="w", format=tarfile.PAX_FORMAT, dereference=False) as tree:
                    add(tree, source, relative)
                stream.flush()
                stream.seek(0)
                checksum = hashlib.file_digest(stream, "sha256").hexdigest()
                size = stream.seek(0, 2)
            name = destination.relative_to(artifacts).as_posix()
            record = {"path": name, "sha256": checksum, "size": size,
                      "type": "tree_archive", "root": relative.as_posix()}
            require(name not in retained or retained[name] == record, f"Conflicting build outputs: {name}")
            if name not in retained:
                temporary.replace(destination)
                retained[name] = record
            return record
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def copy_output(source: Path, relative: PurePosixPath) -> list[dict]:
        source = source.resolve()
        require(source.is_relative_to(work_dir), f"Build output escapes work-dir: {source}")
        destination = outputs / relative
        if source.is_dir():
            return [archive_tree(source, relative)]
        require(source.is_file(), f"Missing regular build output: {source}")
        with source.open("rb") as stream:
            checksum = hashlib.file_digest(stream, "sha256").hexdigest()
        name = (PurePosixPath("outputs") / relative).as_posix()
        record = {"path": name, "sha256": checksum, "size": source.stat().st_size}
        require(name not in retained or retained[name] == record, f"Conflicting build outputs: {name}")
        if name not in retained:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            retained[name] = record
        return [record]

    def files(set_id: str, ancestors: frozenset = frozenset()) -> list[dict]:
        require(set_id in sets and set_id not in ancestors, f"Missing or cyclic output file set: {set_id}")
        group = sets[set_id]
        result = list(group.get("files", []))
        for child in group.get("fileSets", []):
            result.extend(files(child["id"], ancestors | {set_id}))
        return result

    index = {}
    for label in labels:
        target = completed.get(label, {})
        require(target.get("success") is True, f"Required build target did not complete: {label}")
        declared = []
        for group in target.get("outputGroup", []):
            if group["name"] == "default":
                require(not group.get("incomplete", False), f"Incomplete outputs for {label}")
                for file_set in group.get("fileSets", []):
                    declared.extend(files(file_set["id"]))
        tree_paths = [PurePosixPath(path) for path in declared_trees.get(label, [])]
        require(bool(declared or tree_paths), f"Required build target has no default outputs: {label}")
        records = {}
        for tree_path in tree_paths:
            require(execution_root is not None, "Declared directories require an execution root")
            require(bool(tree_path.parts) and tree_path.parts[0] == "bazel-out"
                    and ".." not in tree_path.parts and "\\" not in str(tree_path),
                    f"Unsafe declared tree path: {tree_path}")
            source = execution_root / tree_path
            require(source.is_dir(), f"Declared output tree is not a directory: {source}")
            for record in copy_output(source, tree_path):
                records[record["path"]] = record
        for output in declared:
            uri = urlparse(output.get("uri", ""))
            require(uri.scheme == "file" and uri.netloc in ("", "localhost")
                    and not uri.query and not uri.fragment,
                    f"Build output must be a local file: {output.get('uri')}")
            name = "/".join([*output.get("pathPrefix", []), output["name"]])
            relative = PurePosixPath(name)
            require(bool(relative.parts) and not relative.is_absolute() and ".." not in relative.parts
                    and "\\" not in name, f"Unsafe build output path: {name}")
            if any(relative.is_relative_to(tree_path) for tree_path in tree_paths):
                # These are expanded members of an already archived declared
                # tree, not independent file outputs. Match physical identity
                # as well as the exact logical boundary before skipping them.
                require(Path(unquote(uri.path)).resolve() == (execution_root / relative).resolve(),
                        f"Expanded tree member does not match its execution-root path: {name}")
                continue
            for record in copy_output(Path(unquote(uri.path)), relative):
                records[record["path"]] = record
        index[label] = [records[path] for path in sorted(records)]
    (artifacts / "outputs.json").write_text(json.dumps(index, indent=2) + "\n")


def run_logged(command: list[str], cwd: Path, log: Path) -> None:
    print(f"Running Bazel validation; log: {log}", flush=True)
    with log.open("w") as output:
        result = subprocess.run(command, cwd=cwd, stdout=output, stderr=subprocess.STDOUT)
    if result.returncode:
        print(log.read_text()[-16000:], file=sys.stderr)
        raise RegistryError(f"Command failed with status {result.returncode}; see {log}")


def prepare_rust(config: dict, consumer: Path, work_dir: Path, artifacts: Path,
                 bazel: str, flags: list[str]) -> list[str]:
    """Prepare the registry-fetched Rust graph before its extension is evaluated."""
    preparation = config.get("rust_preparation")
    if preparation is None:
        return []
    revision = preparation["helper_revision"]
    url = ("https://raw.githubusercontent.com/securely1g/sonic-build-infra/"
           f"{revision}/tools/rust/prepare.py")
    with urlopen(url, timeout=60) as response:
        source = response.read()
    require(hashlib.sha256(source).hexdigest() == preparation["helper_sha256"],
            "Rust preparation helper checksum mismatch")
    helper = artifacts / "rust-prepare.py"
    helper.write_bytes(source)
    overrides = work_dir / "rust-overrides.bazelrc"
    # The shared module has its own native toolchains. Consumer platform labels
    # and Starlark settings may name repositories that do not exist there.
    preparation_flags = [flag for flag in flags
                         if flag.startswith(("--registry=", "--lockfile_mode="))]
    command = [sys.executable, str(helper), "--workspace", str(consumer),
               "--shared-only", "--shared-dependency",
               f"{preparation['module']}={preparation['repo_name']}",
               "--staging-dir", str(work_dir / "rust-deps"),
               "--overrides-rc", str(overrides),
               "--receipt", str(artifacts / "rust-preparation.json"),
               "--bazel", bazel, "--bazel-startup-arg=--ignore_all_rc_files",
               f"--bazel-startup-arg=--output_user_root={work_dir / 'bazel'}",
               *["--bazel-arg=" + flag for flag in preparation_flags]]
    run_logged(command, consumer, artifacts / "rust-preparation.log")
    # Keep all other runner settings fixed. Only the verified private copy of
    # the selected Rust module may replace a fetched repository.
    lines = [line for line in overrides.read_text().splitlines()
             if line and not line.startswith("#")]
    prefix = f"common --override_module={preparation['module']}="
    require(len(lines) == 1 and lines[0].startswith(prefix),
            "Rust preparation must produce exactly its declared module override")
    staged = Path(lines[0][len(prefix):]).resolve()
    require(staged.is_relative_to((work_dir / "rust-deps").resolve()),
            "Prepared Rust module must stay in its private staging directory")
    for name in ("Cargo.toml", "Cargo.lock", "Cargo.Bazel.lock", "preparation.json", "source-resolution.json"):
        shutil.copy2(staged / name, artifacts / ("shared-rust-" + name))
    shutil.copy2(overrides, artifacts / "rust-overrides.bazelrc")
    return [lines[0].removeprefix("common ")]


def fetched_modules(output_base: Path, module: str) -> list[Path]:
    # Canonical module repositories use module+ (or module+version). Extension
    # repositories start module++extension+repo and have their own declarations.
    # For example, rules_rs generates a separate rules_rust repository.
    return [path for path in (output_base / "external").glob(f"{module}+*/MODULE.bazel")
            if "++" not in path.parent.name]


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
    for dependency in config["consumer_deps"]:
        name, selected_version = dependency["name"], dependency["version"]
        declarations.append(f"single_version_override(module_name = {json.dumps(name)}, "
                            f"version = {json.dumps(selected_version)})")
    if "go_sdk" in config:
        dependencies = {module: module, **{
            dependency["name"]: dependency.get("repo_name", dependency["name"])
            for dependency in config["consumer_deps"]
        }}
        extension = f"@{dependencies['rules_go']}//go:extensions.bzl"
        declarations.extend([
            f"go_sdk = use_extension({json.dumps(extension)}, \"go_sdk\")",
            f"go_sdk.download(version = {json.dumps(config['go_sdk']['version'])})",
        ])
    if "rust_toolchain" in config:
        dependencies = {module: module, **{
            dependency["name"]: dependency.get("repo_name", dependency["name"])
            for dependency in config["consumer_deps"]
        }}
        extension = f"@{dependencies['rules_rs']}//rs:rules_rust_reexported_extensions.bzl"
        # rules_rs' legacy Rust extension needs a root declaration even when a
        # dependency registers the same toolchain. Match real component roots.
        declarations.extend([
            f"rust = use_extension({json.dumps(extension)}, \"rust\")",
            'rust.toolchain(edition = "2021", '
            'extra_target_triples = ["aarch64-unknown-linux-gnu", "x86_64-unknown-linux-gnu"], '
            f"versions = [{json.dumps(config['rust_toolchain']['version'])}])",
            'use_repo(rust, "rust_toolchains")',
            'register_toolchains("@rust_toolchains//:all")',
        ])
        if config["rust_toolchain"].get("mangled_allocator_libraries", False):
            declarations.extend([
                f'rules_rust = use_extension("@{dependencies["rules_rs"]}//rs:rules_rust.bzl", "rules_rust")',
                'use_repo(rules_rust, "rules_rust")',
            ])
        if config["rust_toolchain"].get("bindgen", False):
            declarations.extend([
                f'bindgen = use_extension("@{dependencies["rules_rs"]}//rs:rules_rust_bindgen.bzl", "rules_rust_bindgen")',
                'use_repo(bindgen, "rules_rust_bindgen")',
                'register_toolchains("@rules_rust_bindgen//:all")',
            ])
    (consumer / "MODULE.bazel").write_text("\n\n".join(declarations) + "\n")
    (consumer / "BUILD.bazel").write_text("# Explicit external targets are built from this consumer.\n")
    (consumer / ".bazelversion").write_text("8.5.1\n")
    (consumer / ".gitignore").write_text("MODULE.bazel.lock\n")
    shutil.copy2(consumer / "MODULE.bazel", artifacts / "consumer.MODULE.bazel")
    prefix = [bazel, "--ignore_all_rc_files", f"--output_user_root={work_dir / 'bazel'}"]
    flags = [f"--registry={root.resolve().as_uri()}", "--registry=https://bcr.bazel.build/",
             f"--platforms={config['platforms'][architecture]}", "--lockfile_mode=update",
             *config.get("build_flags", [])]
    if config.get("rust_toolchain", {}).get("mangled_allocator_libraries", False):
        flags.append("--@rules_rust//rust/settings:experimental_use_allocator_libraries_with_mangled_symbols=True")
    try:
        flags.extend(prepare_rust(config, consumer, work_dir, artifacts, bazel, flags))
        run_logged([*prefix, "build", *flags, f"--build_event_json_file={artifacts / 'build-events.jsonl'}",
                    *config["build_targets"]], consumer, artifacts / "build.log")
        declared_trees = query_output_trees(prefix, flags, config["build_targets"], consumer, artifacts)
        # Path queries need dependency resolution, but not target/host platform
        # flags whose apparent labels may be unresolved in a fresh info command.
        info_flags = [flag for flag in flags if flag.startswith(
            ("--registry=", "--lockfile_mode=", "--override_module=", "--override_repository="))]
        execution_root = Path(subprocess.check_output([*prefix, "info", *info_flags, "execution_root"],
                                                     cwd=consumer, text=True).strip())
        collect_outputs(artifacts / "build-events.jsonl", config["build_targets"], work_dir, artifacts,
                        declared_trees, execution_root)
        run_logged([*prefix, "test", *flags, "--nocache_test_results", "--test_output=errors",
                    f"--build_event_json_file={artifacts / 'test-events.jsonl'}", *config["test_targets"]],
                   consumer, artifacts / "test.log")
        verify_tests(artifacts / "test-events.jsonl", config["test_targets"])
        output_base = Path(subprocess.check_output([*prefix, "info", *info_flags, "output_base"],
                                                  cwd=consumer, text=True).strip())
        fetched = fetched_modules(output_base, module)
        require(len(fetched) == 1, f"Expected one fetched repository for {module}, found {len(fetched)}")
        registry_module = root / "modules" / module / version / "MODULE.bazel"
        require(parse_module_identity(fetched[0].read_text()) == (module, version),
                "Fetched source module name/version differs from requested registry entry")
        canonical_bytes = registry_module.read_bytes()
        fetched_bytes = fetched[0].read_bytes()
        # Bazel materializes the registry's MODULE after applying source
        # overlays/patches. The generated overlay is checked independently at
        # entry validation; its banner is not part of the fetched MODULE.
        require(fetched_bytes == canonical_bytes,
                "Fetched MODULE.bazel differs from registry MODULE.bazel")
        shutil.copy2(fetched[0], artifacts / "fetched.MODULE.bazel")
        for dependency in config["consumer_deps"]:
            name, selected_version = dependency["name"], dependency["version"]
            selected = fetched_modules(output_base, name)
            require(len(selected) == 1, f"Expected one fetched repository for consumer dependency {name}")
            require(parse_module_identity(selected[0].read_text()) == (name, selected_version),
                    f"Fetched consumer dependency {name} differs from the declared version {selected_version}")
            shutil.copy2(selected[0], artifacts / f"consumer-dep-{name}.MODULE.bazel")
        require((consumer / "MODULE.bazel.lock").is_file(), "Bazel did not generate MODULE.bazel.lock resolution evidence")
        (artifacts / "validation.json").write_text(json.dumps({
            "module": module, "version": version, "architecture": architecture,
            "build_targets": config["build_targets"], "passed_tests": config["test_targets"],
            "build_flags": config.get("build_flags", []),
            "consumer_deps": config["consumer_deps"],
            "go_sdk": config.get("go_sdk"),
            "rust_toolchain": config.get("rust_toolchain"),
            "rust_preparation": config.get("rust_preparation"),
            "generated_module_overlay": config.get("generated_module_overlay", False),
            "fetched_module_matches_registry": fetched_bytes == canonical_bytes,
            "registry_module_sha256": hashlib.sha256(canonical_bytes).hexdigest(),
            "fetched_module_sha256": hashlib.sha256(fetched_bytes).hexdigest(),
            "generated_module_overlay_sha256": (hashlib.sha256(module_overlay_bytes(
                registry_module.parent, module, version)).hexdigest()
                if config.get("generated_module_overlay") else None),
        }, indent=2) + "\n")
    finally:
        lockfile = consumer / "MODULE.bazel.lock"
        if lockfile.is_file():
            shutil.copy2(lockfile, artifacts / "MODULE.bazel.lock")
        testlogs = consumer / "bazel-testlogs"
        if testlogs.exists():
            shutil.copytree(testlogs, artifacts / "testlogs", dirs_exist_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    planner = subparsers.add_parser("plan")
    planner.add_argument("--base")
    planner.add_argument("--head")
    scope = planner.add_mutually_exclusive_group()
    scope.add_argument("--all", action="store_true", dest="all_versions",
                       help="test every configured version, including historical versions")
    scope.add_argument("--latest", action="store_true", dest="latest_versions",
                       help="test the latest non-yanked version of each configured module")
    planner.add_argument("--output", required=True, type=Path)
    synchronizer = subparsers.add_parser("sync-module", help="generate or check an opted-in MODULE overlay")
    synchronizer.add_argument("--module", required=True)
    synchronizer.add_argument("--version", required=True)
    synchronizer.add_argument("--check", action="store_true", help="check generated bytes and checksum without writing")
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
            result = plan(ROOT, args.base, args.head, args.all_versions, args.latest_versions)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(result, indent=2) + "\n")
            print(json.dumps(result, separators=(",", ":")))
            print(f"Selected {len(result['include'])} native validation jobs", file=sys.stderr)
        elif args.command == "sync-module":
            sync_module(ROOT, args.module, args.version, args.check)
        else:
            run(ROOT, args.module, args.version, args.architecture, args.work_dir, args.artifacts, args.bazel)
    except (RegistryError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Registry CI failed: {error}\n")


if __name__ == "__main__":
    main()
