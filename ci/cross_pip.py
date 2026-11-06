"""Select locked Python wheels for both native tools and ARM target tests."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil


SUPPORTED_ARGUMENTS = {
    "hub_name", "python_version", "requirements_lock", "download_only", "quiet",
    "timeout", "isolated", "enable_implicit_namespace_pkgs",
}


def simple_hubs(module_text: str) -> list[dict]:
    """Find literal, non-dev pip hubs without changing existing platform/index settings."""
    statements = ast.parse(module_text).body
    aliases = set()
    for statement in statements:
        if not isinstance(statement, ast.Assign) or not isinstance(statement.value, ast.Call):
            continue
        call = statement.value
        if not isinstance(call.func, ast.Name) or call.func.id != "use_extension":
            continue
        if len(call.args) < 2 or not all(isinstance(arg, ast.Constant) for arg in call.args[:2]):
            continue
        label, extension = [arg.value for arg in call.args[:2]]
        if extension != "pip" or not isinstance(label, str) or not label.endswith("//python/extensions:pip.bzl"):
            continue
        dev = next((item.value for item in call.keywords if item.arg == "dev_dependency"), None)
        if dev is not None and ast.literal_eval(dev):
            continue
        aliases.update(target.id for target in statement.targets if isinstance(target, ast.Name))

    hubs = []
    # Comprehensions/tool-only hubs and explicitly platform-specific configurations
    # keep their published behavior. No Starlark or Python source is executed here.
    for statement in statements:
        if not isinstance(statement, ast.Expr) or not isinstance(statement.value, ast.Call):
            continue
        call = statement.value
        if not (isinstance(call.func, ast.Attribute) and call.func.attr == "parse"
                and isinstance(call.func.value, ast.Name) and call.func.value.id in aliases):
            continue
        keys = {item.arg for item in call.keywords}
        if "requirements_lock" not in keys or "experimental_index_url" in keys:
            continue
        if call.args or not keys <= SUPPORTED_ARGUMENTS:
            raise ValueError("Cross pip hub has unsupported arguments; retain its original configuration explicitly")
        try:
            arguments = {item.arg: ast.literal_eval(item.value) for item in call.keywords}
        except (ValueError, TypeError) as error:
            raise ValueError("Cross pip hub arguments must be literal values") from error
        if not all(isinstance(arguments.get(key), str) and arguments[key]
                   for key in ("hub_name", "python_version", "requirements_lock")):
            raise ValueError("Cross pip hub requires a name, Python version, and locked requirements")
        relative_lock(arguments["requirements_lock"])
        hubs.append(arguments)
    return hubs


def relative_lock(label: str) -> Path:
    if not label.startswith("//") or ":" not in label or "\x00" in label:
        raise ValueError("Cross pip requirements must be a file in the original module")
    package, target = label[2:].split(":", 1)
    path = PurePosixPath(package) / target
    if not target or path.is_absolute() or ".." in path.parts or ":" in target:
        raise ValueError("Cross pip requirements path escapes its original module")
    return Path(*path.parts)


def prepare(root: Path, consumer: Path, artifacts: Path, prefix: list[str],
            flags: list[str], versions: dict[str, str], toolchains) -> dict | None:
    """Override only generated pip hubs; preserve source files and selected versions."""
    hubs = []
    for module, version in sorted(versions.items()):
        source = root / "modules" / module / version / "MODULE.bazel"
        if source.is_file():
            for arguments in simple_hubs(source.read_text()):
                hubs.append({"module": module, "version": version, "arguments": arguments,
                             "module_sha256": hashlib.sha256(source.read_bytes()).hexdigest()})
    if not hubs:
        return None
    python_version = versions.get("rules_python", "")
    if not python_version:
        raise ValueError("Cross wheel selection requires the consumer's existing rules_python")
    python_repo = toolchains.expose_dependency(consumer, "rules_python", versions)
    module_path = consumer / "MODULE.bazel"
    text = module_path.read_text()
    variable = "registry_ci_cross_pip"
    if variable in text:
        raise ValueError("Generated cross pip extension already exists in the consumer")
    declarations = [
        f'{variable} = use_extension("@{python_repo}//python/extensions:pip.bzl", "pip")',
    ]
    overrides = {}
    for hub in hubs:
        repo = toolchains.expose_dependency(consumer, hub["module"], versions)
        original = hub["arguments"]
        key = hub["module"] + "/" + original["hub_name"]
        generated = "registry_ci_pip_" + hashlib.sha256(key.encode()).hexdigest()[:16]
        if original["hub_name"] in overrides and overrides[original["hub_name"]] != generated:
            raise ValueError("Multiple modules declare the same pip hub")
        overrides[original["hub_name"]] = generated
        arguments = dict(original, hub_name=generated,
                         requirements_lock="@" + repo + original["requirements_lock"],
                         experimental_index_url="https://pypi.org/simple")
        declarations.append(f"{variable}.parse(" + ", ".join(
            f"{key}={value!r}" for key, value in sorted(arguments.items())) + ")")
        hub["generated_hub"] = generated
        hub["source_repository"] = repo
    for original, generated in sorted(overrides.items()):
        declarations.append(f'use_repo({variable}, {generated!r})')
        declarations.append(f'override_repo({variable}, **{{{original!r}: {generated!r}}})')
    module_path.write_text(module_path.read_text() + "\n# CI target-aware wheels from unchanged locks.\n"
                           + "\n".join(declarations) + "\n")
    after = toolchains.module_graph(prefix, flags, consumer, artifacts, "cross-pip-graph")
    if after != versions:
        raise ValueError("Cross pip hubs changed the consumer's selected module versions")
    receipt = {"rules_python_version": python_version, "module_versions_unchanged": True, "hubs": hubs}
    (artifacts / "cross-pip-hubs.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


def record_locks(receipt: dict | None, output_base: Path, artifacts: Path, fetched_modules) -> None:
    if receipt is None:
        return
    destination = artifacts / "cross-pip-locks"
    destination.mkdir()
    for index, hub in enumerate(receipt["hubs"]):
        modules = fetched_modules(output_base, hub["module"])
        if len(modules) != 1:
            raise ValueError(f"Expected one fetched source for cross pip hub in {hub['module']}")
        module = modules[0]
        if hashlib.sha256(module.read_bytes()).hexdigest() != hub["module_sha256"]:
            raise ValueError("Cross pip source MODULE differs from its registry entry")
        lock = module.parent / relative_lock(hub["arguments"]["requirements_lock"])
        if not lock.resolve().is_relative_to(module.parent.resolve()):
            raise ValueError("Cross pip requirements resolve outside their source module")
        hub["requirements_lock_sha256"] = hashlib.sha256(lock.read_bytes()).hexdigest()
        output = destination / f"{index:02}-{hub['module']}-{hub['arguments']['python_version']}.txt"
        shutil.copy2(lock, output)
        hub["lock_evidence"] = str(output.relative_to(artifacts))
    (artifacts / "cross-pip-hubs.json").write_text(json.dumps(receipt, indent=2) + "\n")
