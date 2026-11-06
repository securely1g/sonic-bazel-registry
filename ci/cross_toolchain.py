"""CI-local ARM platforms and an isolated, pinned native cross-compiler provider.

The provider resolves in its own workspace. Its dependencies never participate
in the module under test's resolution; only declared compiler/sysroot files are
imported through a local repository.
"""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import shutil
import subprocess


PROVIDER_VERSION = "0.0.25-34de7330abc72229dfc8dab88dec71b89c52aa88"
PACKAGE = "_registry_ci_cross"
REPOSITORY = "registry_ci_cross_cc"
COMPILER_REPOSITORY = "sonic-build-infra++gcc+gcc-14.2.0-linux-target-aarch64-host-x86_64"
SYSROOT_REPOSITORY = "sonic-build-infra++sysroots+sonic_sysroot"
SONIC_PLATFORMS = {
    "@sonic_build_infra//platforms:aarch64_trixie",
    "@sonic-build-infra//platforms:aarch64_trixie",
}
# These immutable entries register a Trixie GCC toolchain with distinct
# AMD64 execution and ARM64 target constraints. A platform label or a newer
# version alone does not prove that registration; runtime acceptance is separate.
VERIFIED_SONIC_CROSS_VERSIONS = {
    "0.0.17-8baf1ad829c5095297d85148b042145b87d623a3",
    "0.0.22-a12bc826d6f811a157db5c7c02a2fe033896cc14",
    "0.0.23-5b224d7190d04f1b7b68429eedfc03b7b1565ed0",
    "0.0.25-17a1e555291c64be1a6ff008f33352bffc4f8e5c",
    "0.0.25-34de7330abc72229dfc8dab88dec71b89c52aa88",
    "0.0.26-51c838da6ff57295fde6e0bc3807841cb31a8568",
}


def resolution_flags(flags: list[str]) -> list[str]:
    return [flag for flag in flags if flag.startswith((
        "--registry=", "--lockfile_mode=", "--experimental_downloader_config=",
        "--downloader_config=", "--http_connector_", "--http_max_parallel_downloads=",
        "--repository_cache=", "--override_module=", "--override_repository=",
    ))]


def selected_versions(graph: dict) -> dict[str, str]:
    versions = {}

    def visit(value):
        if isinstance(value, dict):
            if value.get("key") != "<root>" and "name" in value and "version" in value:
                name, version = value["name"], value["version"]
                if name in versions and versions[name] != version:
                    raise ValueError(f"Cross adapter cannot alias multiple selected versions of {name}")
                versions[name] = version
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(graph)
    return versions


def module_graph(prefix: list[str], flags: list[str], consumer: Path, artifacts: Path,
                 name: str) -> dict[str, str]:
    command = [*prefix, "mod", "graph", *resolution_flags(flags), "--output=json"]
    (artifacts / (name + "-command.json")).write_text(json.dumps(command, indent=2) + "\n")
    with (artifacts / (name + ".json")).open("w") as output, (artifacts / (name + ".stderr")).open("w") as errors:
        subprocess.run(command, cwd=consumer, stdout=output, stderr=errors, check=True)
    return selected_versions(json.loads((artifacts / (name + ".json")).read_text()))


def expose_dependency(consumer: Path, name: str, versions: dict[str, str]) -> str:
    """Expose an already selected module, retaining any existing apparent name."""
    path = consumer / "MODULE.bazel"
    text = path.read_text()
    for statement in ast.parse(text).body:
        if not isinstance(statement, ast.Expr) or not isinstance(statement.value, ast.Call):
            continue
        call = statement.value
        if not isinstance(call.func, ast.Name) or call.func.id != "bazel_dep":
            continue
        literals = {item.arg: item.value.value for item in call.keywords
                    if isinstance(item.value, ast.Constant)}
        if literals.get("name") == name:
            return literals.get("repo_name", name)
    if name not in versions:
        raise ValueError(f"Cross adapter requires {name} to be present in the original module graph")
    path.write_text(text + f"\n# CI alias of the existing selected version; no dependency upgrade.\n"
                    f"bazel_dep(name={json.dumps(name)}, version={json.dumps(versions[name])})\n")
    return name


def write_platforms(consumer: Path, target_parent: str, execution_parent: str,
                    platforms_repo: str, trixie: str) -> dict:
    directory = consumer / PACKAGE
    if directory.exists():
        raise ValueError(f"Generated cross-platform package already exists: {directory}")
    directory.mkdir()
    lines = ['package(default_visibility=["//visibility:public"])']
    for name, parent, cpu in (("arm64", target_parent, "aarch64"),
                              ("amd64", execution_parent, "x86_64")):
        constraints = [f"@{platforms_repo}//os:linux", f"@{platforms_repo}//cpu:{cpu}", trixie]
        lines.append(f"platform(name={json.dumps(name)}, parents=[{json.dumps(parent)}], "
                     f"constraint_values={json.dumps(constraints)})")
    (directory / "BUILD.bazel").write_text("\n".join(lines) + "\n")
    return {"declared_target_platform": target_parent, "declared_execution_platform": execution_parent,
            "target_platform": f"//{PACKAGE}:arm64", "execution_platform": f"//{PACKAGE}:amd64",
            "target_cpu": "aarch64", "execution_cpu": "x86_64", "os": "linux",
            "distribution_constraint": trixie}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare_provider(root: Path, work: Path, artifacts: Path, prefix: list[str],
                     flags: list[str], run_logged) -> dict:
    provider = work / "cross-provider"
    provider.mkdir()
    module = f'''module(name="registry_ci_cross_provider")
bazel_dep(name="sonic-build-infra", version="{PROVIDER_VERSION}", repo_name="sonic_build_infra")
gcc = use_extension("@sonic_build_infra//toolchains/gcc:extensions.bzl", "gcc")
use_repo(gcc, registry_ci_gcc="gcc-14.2.0-linux-target-aarch64-host-x86_64")
sysroots = use_extension("@sonic_build_infra//toolchains/sysroot:extensions.bzl", "sysroots")
use_repo(sysroots, registry_ci_sysroot="sonic_sysroot")
'''
    (provider / "MODULE.bazel").write_text(module)
    (provider / "BUILD.bazel").write_text("")
    # A distinct output base also isolates callers that set --output_base.
    provider_prefix = [*prefix, f"--output_base={provider / 'bazel-output'}"]
    provider_flags = [flag for flag in resolution_flags(flags)
                      if not flag.startswith(("--override_module=", "--override_repository="))]
    try:
        run_logged([*provider_prefix, "fetch", *provider_flags,
                    "--repo=@registry_ci_gcc", "--repo=@registry_ci_sysroot"], provider, artifacts / "cross-provider-fetch.log")
        output_base = provider / "bazel-output"
        compiler = output_base / "external" / COMPILER_REPOSITORY
        sysroot = output_base / "external" / SYSROOT_REPOSITORY
        expected = root / "modules/sonic-build-infra" / PROVIDER_VERSION
        fetched = output_base / "external/sonic-build-infra+/MODULE.bazel"
        if fetched.read_bytes() != (expected / "MODULE.bazel").read_bytes():
            raise ValueError("Cross compiler provider MODULE differs from the pinned registry entry")
        for name, source in (("provider.MODULE.bazel", provider / "MODULE.bazel"),
                             ("provider.MODULE.bazel.lock", provider / "MODULE.bazel.lock"),
                             ("provider-source.json", expected / "source.json"),
                             ("provider-fetched.MODULE.bazel", fetched),
                             ("compiler-inputs.json", compiler / "inputs.json"),
                             ("sysroot-inputs.json", sysroot / "inputs.json")):
            shutil.copy2(source, artifacts / ("cross-" + name))
        compiler_program = compiler / "usr/bin/aarch64-linux-gnu-gcc-14"
        header = compiler_program.read_bytes()[:20]
        if header[:4] != b"\x7fELF" or int.from_bytes(header[18:20], "little") != 62:
            raise ValueError("Cross compiler must be a native AMD64 executable")
        return {"module": "sonic-build-infra", "version": PROVIDER_VERSION,
                "compiler": str(compiler), "sysroot": str(sysroot / "root"),
                "compiler_elf_machine": 62, "compiler_sha256": _sha256(compiler_program),
                "compiler_manifest_sha256": _sha256(compiler / "inputs.json"),
                "sysroot_manifest_sha256": _sha256(sysroot / "inputs.json"),
                "provider_lock_sha256": _sha256(provider / "MODULE.bazel.lock"),
                "registry_module_sha256": _sha256(expected / "MODULE.bazel")}
    finally:
        # The compiler files remain available, but the provider's JVM must not
        # compete with the tested consumer and its compiler actions for memory.
        run_logged([*provider_prefix, "shutdown"], provider, artifacts / "cross-provider-shutdown.log")


def write_adapter(consumer: Path, work: Path, provider: dict, rules_cc_repo: str,
                  platforms_repo: str) -> Path:
    adapter = work / "cross-cc-repository"
    adapter.mkdir()
    (adapter / "compiler").mkdir()
    (adapter / "sysroot").mkdir()
    # Omit provider BUILD files so they cannot introduce nested Bazel packages.
    for name in ("bin", "usr", "aarch64-linux-gnu", "inputs.json"):
        (adapter / "compiler" / name).symlink_to(Path(provider["compiler"]) / name)
    for source in Path(provider["sysroot"]).iterdir():
        if source.name not in ("BUILD", "BUILD.bazel"):
            (adapter / "sysroot" / source.name).symlink_to(source)
    (adapter / "WORKSPACE").write_text(f'workspace(name="{REPOSITORY}")\n')
    shutil.copy2(Path(__file__).with_name("cross_cc_toolchain.bzl"), adapter / "config.bzl")
    for name in ("aarch64-linux-gnu-gcc", "aarch64-linux-gnu-g++"):
        shutil.copy2(Path(__file__).with_name("cross_gcc"), adapter / name)
    (adapter / "BUILD.bazel").write_text(f'''load("@{rules_cc_repo}//cc:defs.bzl", "cc_toolchain")
load(":config.bzl", "linux_aarch64_gcc")
package(default_visibility=["//visibility:public"])
constraint_setting(name="distribution")
constraint_value(name="trixie", constraint_setting=":distribution")
filegroup(name="all_files", srcs=glob([
    "aarch64-linux-gnu-gcc", "aarch64-linux-gnu-g++", "compiler/bin/**", "compiler/usr/bin/**", "compiler/usr/lib/**", "compiler/usr/libexec/**",
    "compiler/aarch64-linux-gnu/**", "compiler/inputs.json", "sysroot/**",
]))
filegroup(name="empty")
linux_aarch64_gcc(name="config", compiler_anchor="compiler/inputs.json", sysroot_anchor="sysroot/usr/include/features.h")
cc_toolchain(name="cc", toolchain_identifier="registry-ci-aarch64-gcc14", toolchain_config=":config",
    all_files=":all_files", ar_files=":all_files", as_files=":all_files", compiler_files=":all_files",
    dwp_files=":empty", linker_files=":all_files", objcopy_files=":all_files", strip_files=":all_files",
    supports_param_files=1)
toolchain(name="toolchain", toolchain=":cc", toolchain_type="@bazel_tools//tools/cpp:toolchain_type",
    exec_compatible_with=["@{platforms_repo}//os:linux", "@{platforms_repo}//cpu:x86_64", ":trixie"],
    target_compatible_with=["@{platforms_repo}//os:linux", "@{platforms_repo}//cpu:aarch64", ":trixie"])
''')
    module = consumer / "MODULE.bazel"
    module.write_text(module.read_text() + f'''
# CI-only compiler files from a separately resolved, pinned provider.
registry_ci_local_repository = use_repo_rule("@bazel_tools//tools/build_defs/repo:local.bzl", "local_repository")
registry_ci_local_repository(name="{REPOSITORY}", path={json.dumps(str(adapter))})
register_toolchains("@{REPOSITORY}//:toolchain")
''')
    return adapter


def prepare(root: Path, consumer: Path, work: Path, artifacts: Path, prefix: list[str],
            flags: list[str], target_parent: str, execution_parent: str, run_logged) -> dict:
    """Adapt generated consumer inputs, preserving its selected module versions."""
    shutil.copy2(consumer / "MODULE.bazel", artifacts / "consumer-before-cross.MODULE.bazel")
    before = module_graph(prefix, flags, consumer, artifacts, "cross-graph-before")
    platforms_repo = expose_dependency(consumer, "platforms", before)
    provider = None
    adapter = None
    sonic_version = before.get("sonic-build-infra")
    use_published_toolchain = (target_parent in SONIC_PLATFORMS
                               and sonic_version in VERIFIED_SONIC_CROSS_VERSIONS)
    if not use_published_toolchain:
        rules_cc_repo = expose_dependency(consumer, "rules_cc", before)
        run_logged([*prefix, "shutdown"], consumer, artifacts / "cross-consumer-before-provider-shutdown.log")
        provider = prepare_provider(root, work, artifacts, prefix, flags, run_logged)
        adapter = write_adapter(consumer, work, provider, rules_cc_repo, platforms_repo)
        trixie = f"@{REPOSITORY}//:trixie"
    else:
        # Only the exact graph-selected entries above have proven registration.
        # Retain their distro constraint and all inherited platform constraints.
        trixie = target_parent.rsplit(":", 1)[0] + ":trixie"
    result = write_platforms(consumer, target_parent, execution_parent, platforms_repo, trixie)
    after = module_graph(prefix, flags, consumer, artifacts, "cross-graph-after")
    if before != after:
        raise ValueError("Cross adapter changed the consumer's selected module versions")
    result.update(provider=provider, selected_module_versions=before, module_versions_unchanged=True,
                  selected_sonic_build_infra_version=sonic_version,
                  use_published_cross_toolchain=use_published_toolchain)
    shutil.copy2(consumer / PACKAGE / "BUILD.bazel", artifacts / "cross-platforms.BUILD.bazel")
    if adapter:
        shutil.copy2(adapter / "BUILD.bazel", artifacts / "cross-adapter.BUILD.bazel")
        shutil.copy2(adapter / "config.bzl", artifacts / "cross-adapter-config.bzl")
    (artifacts / "cross-platforms.json").write_text(json.dumps(result, indent=2) + "\n")
    return result
