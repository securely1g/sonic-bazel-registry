"""Original CPython control policy using the shared public metadata engine."""
load("@sonic_build_infra//oci:runtime_packages.bzl", "RuntimePackagesInfo")
load("@tar.bzl//tar:tar.bzl", "tar_lib")

def _one(target):
    files = target[DefaultInfo].files.to_list()
    if len(files) != 1:
        fail("Expected one original package input: " + str(target.label))
    return files[0]

def _impl(ctx):
    spec = ctx.actions.declare_file(ctx.label.name + ".inputs.json")
    receipt = ctx.actions.declare_file(ctx.label.name + ".receipt.json")
    output = ctx.actions.declare_file(ctx.label.name + ".json") if ctx.attr.mode == "metadata" else None
    tree = ctx.actions.declare_directory(ctx.label.name + ".packages") if ctx.attr.mode == "metadata" else None
    tar = ctx.toolchains[tar_lib.toolchain_type]
    inputs = [ctx.file.control, ctx.file.changelog, ctx.file.rules, ctx.file._tools]
    dependencies = depset(transitive = [target[RuntimePackagesInfo].trees for target in ctx.attr.dependencies])
    data = {"architecture": "arm64" if ctx.target_platform_has_constraint(ctx.attr._arm64[platform_common.ConstraintValueInfo]) else "amd64", "mode": ctx.attr.mode, "control": ctx.file.control.path, "changelog": ctx.file.changelog.path,
            "rules": ctx.file.rules.path, "tools": ctx.file._tools.path, "tar": tar.tarinfo.binary.path,
            "output": output.path if output else "", "tree": tree.path if tree else "", "receipt": receipt.path,
            "dependencies": [file.path for file in dependencies.to_list()],
            "packages": {}, "debian_files": {}, "symbols": {}, "apt": [],
            "source_outputs": {}, "binary_outputs": {}}
    for name, target in ctx.attr.packages.items():
        file = _one(target)
        inputs.append(file)
        data["packages"][name] = {"label": "//python:" + name + ".runtime", "tar": file.path}
    for name, target in ctx.attr.debian_files.items():
        file = _one(target)
        inputs.append(file)
        data["debian_files"][name] = file.path
    for name, target in ctx.attr.symbols.items():
        file = _one(target)
        inputs.append(file)
        data["symbols"][name] = file.path
    for payload, control in zip(ctx.attr.apt_data + ctx.attr._abi_data, ctx.attr.apt_controls + ctx.attr._abi_controls):
        a, z = _one(payload), _one(control)
        inputs.extend([a, z])
        data["apt"].append([a.path, z.path])
    outputs = [receipt]
    groups = {"receipt": depset([receipt])}
    if ctx.attr.mode == "controls":
        for package in ctx.attr.packages:
            source = ctx.actions.declare_file(ctx.label.name + "/" + package + ".source-control")
            binary = ctx.actions.declare_file(ctx.label.name + "/" + package + ".binary-control")
            outputs.extend([source, binary])
            data["source_outputs"][package] = source.path
            data["binary_outputs"][package] = binary.path
            key = package.replace(".", "_").replace("-", "_")
            groups[key] = depset([source])
            groups[key + "_binary"] = depset([binary])
    else:
        data["expected_control"] = ctx.file.expected_control.path
        inputs.append(ctx.file.expected_control)
        outputs.extend([output, tree])
    ctx.actions.write(spec, json.encode_indent(data) + "\n")
    ctx.actions.run(executable = ctx.executable._tool, arguments = [spec.path],
                    inputs = depset(inputs + [spec], transitive = [dependencies]),
                    tools = tar.default.files, outputs = outputs,
                    env = {"LANG": "C", "LC_ALL": "C", "PYTHONHASHSEED": "0"},
                    mnemonic = "CPythonOriginalControls" if ctx.attr.mode == "controls" else "CPythonRuntimeMetadata")
    result = [DefaultInfo(files = depset(outputs if ctx.attr.mode == "controls" else [output])), OutputGroupInfo(**groups)]
    if ctx.attr.mode == "metadata":
        result.append(RuntimePackagesInfo(metadata = output, trees = depset([tree], transitive = [dependencies])))
    return result

python_original_metadata = rule(implementation = _impl, toolchains = [tar_lib.toolchain_type], attrs = {
    "_arm64": attr.label(default = Label("@platforms//cpu:aarch64")),
    "mode": attr.string(mandatory = True, values = ["controls", "metadata"]),
    "packages": attr.string_keyed_label_dict(mandatory = True),
    "control": attr.label(allow_single_file = True, mandatory = True),
    "changelog": attr.label(allow_single_file = True, mandatory = True),
    "rules": attr.label(allow_single_file = True, mandatory = True),
    "expected_control": attr.label(allow_single_file = True),
    "debian_files": attr.string_keyed_label_dict(allow_files = True), "symbols": attr.string_keyed_label_dict(allow_files = True),
    "dependencies": attr.label_list(providers = [RuntimePackagesInfo]),
    "apt_data": attr.label_list(allow_files = True), "apt_controls": attr.label_list(allow_files = True),
    "_abi_data": attr.label_list(default = [Label("@sysroot//" + name + ":data") for name in ["libc6", "libgcc-s1", "libstdc++6"]]),
    "_abi_controls": attr.label_list(default = [Label("@sysroot//" + name + ":control") for name in ["libc6", "libgcc-s1", "libstdc++6"]]),
    "_tools": attr.label(default = Label("@sonic_build_infra//tools/build_tools:kernel_runtime"), cfg = "exec", allow_single_file = True),
    "_tool": attr.label(default = Label("//python:metadata_bridge"), cfg = "exec", executable = True),
})
