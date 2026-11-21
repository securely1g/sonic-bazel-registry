"""Declared Kbuild compilation, source installation and kernel consumers."""

load("@sonic_build_infra//tools/build_tools:defs.bzl", "PythonRuntimeInfo")
load(":sources.bzl", "KERNEL_SOURCES")
load("@sonic_build_infra//oci:runtime_packages.bzl", "RuntimePackagesInfo")
load("@sonic_build_infra//deb:sonic_deb.bzl", "sonic_deb")

KernelBuildInfo = provider(fields = ["artifacts", "arch", "host_arch", "source_root", "source_files", "build_tools", "raw_files", "runtime_tree", "debug_tree", "receipt", "configuration", "inputs"])
KernelInstallInfo = provider(fields = ["outputs"])
KernelModuleInfo = provider(fields = ["modules", "module_symvers", "kernel"])

KernelConfigInfo = provider(fields = ["values"])

KernelExecutionInfo = provider(fields = ["architecture"])

def _kernel_execution_impl(ctx):
    if not ctx.target_platform_has_constraint(ctx.attr._linux[platform_common.ConstraintValueInfo]):
        fail("Kernel tools require a Linux execution platform")
    for architecture, constraint in [("amd64", ctx.attr._amd64), ("arm64", ctx.attr._arm64)]:
        if ctx.target_platform_has_constraint(constraint[platform_common.ConstraintValueInfo]):
            return [KernelExecutionInfo(architecture = architecture)]
    fail("Kernel tools require an AMD64 or ARM64 execution platform")

# This dependency is configured with cfg = "exec" by the package rule, so its
# target platform is the platform that actually runs the declared build tools.
kernel_execution = rule(
    implementation = _kernel_execution_impl,
    attrs = {
        "_linux": attr.label(default = Label("@platforms//os:linux")),
        "_amd64": attr.label(default = Label("@platforms//cpu:x86_64")),
        "_arm64": attr.label(default = Label("@platforms//cpu:aarch64")),
    },
)

def _kernel_config_impl(ctx):
    values = json.decode(ctx.build_setting_value)
    if type(values) != "dict" or any([type(key) != "string" or type(value) != "string" for key, value in values.items()]):
        fail("Unsupported kernel configuration: expected a JSON object of Make variable strings")
    return [KernelConfigInfo(values = values)]

kernel_config = rule(
    implementation = _kernel_config_impl,
    build_setting = config.string(flag = True),
)

def kernel_configuration(architecture, requested, host_architecture = None):
    """Own capability checks here, rather than in each image consumer."""
    host_architecture = host_architecture or architecture
    if (host_architecture, architecture) not in [
        ("amd64", "amd64"), ("arm64", "arm64"),
        ("amd64", "arm64"), ("amd64", "armhf"),
    ]:
        fail("Unsupported kernel build pair: %s -> %s" % (host_architecture, architecture))
    values = {
        "CONFIGURED_ARCH": architecture,
        "CONFIGURED_PLATFORM": "vs",
        "BLDENV": "trixie",
        "CROSS_BUILD_ENVIRON": "y" if host_architecture != architecture else "n",
        "MULTIARCH_QEMU_ENVIRON": "n",
        "KERNEL_VERSION": "6.12.41",
        "KERNEL_ABISUFFIX": "+deb13",
        "KERNEL_SUBVERSION": "1",
        "KERNEL_FEATURESET": "sonic",
        "KVERSION": "",
        "ADDITIONAL_BUILD_PROFILES": "",
        "SECURE_UPGRADE_MODE": "no_sign",
        "SECURE_UPGRADE_KERNEL_CAFILE": "",
        "INCLUDE_EXTERNAL_PATCHES": "n",
        "EXTERNAL_KERNEL_PATCH_URL": "",
        "EXTERNAL_KERNEL_PATCH_LOC": "",
    }
    defaults = dict(values)
    for key, value in requested.items():
        if key not in values:
            fail("Unsupported kernel configuration: unknown Make variable " + key)
        values[key] = value
    for key in ["CROSS_BUILD_ENVIRON", "MULTIARCH_QEMU_ENVIRON", "INCLUDE_EXTERNAL_PATCHES"]:
        values[key] = values[key] or "n"
    values["SECURE_UPGRADE_MODE"] = values["SECURE_UPGRADE_MODE"].strip('"') or "no_sign"
    if "KVERSION" not in requested:
        suffix = "armmp" if values["CONFIGURED_ARCH"] == "armhf" else values["CONFIGURED_ARCH"]
        values["KVERSION"] = values["KERNEL_VERSION"] + values["KERNEL_ABISUFFIX"] + "-" + values["KERNEL_FEATURESET"] + "-" + suffix
    defaults["KVERSION"] = "6.12.41+deb13-sonic-" + ("armmp" if architecture == "armhf" else architecture)
    for key in sorted(values):
        # Make does not read these inputs while their features are disabled.
        if key == "SECURE_UPGRADE_KERNEL_CAFILE" and values["SECURE_UPGRADE_MODE"] == "no_sign":
            continue
        if key in ["EXTERNAL_KERNEL_PATCH_URL", "EXTERNAL_KERNEL_PATCH_LOC"] and values["INCLUDE_EXTERNAL_PATCHES"] == "n":
            continue
        if values[key] != defaults[key]:
            fail("Unsupported kernel configuration: %s=%r; this producer supports %r" % (key, values[key], defaults[key]))
    return values

def _packages(architecture):
    abi = "6.12.41+deb13-sonic-" + architecture
    suffix = "_6.12.41-1_" + architecture + ".deb"
    return [
        "linux-image-" + abi + "-unsigned" + suffix,
        "linux-image-" + abi + "-dbg" + suffix,
        "linux-headers-" + abi + suffix,
        "linux-headers-6.12.41+deb13-common-sonic_6.12.41-1_all.deb",
        "linux-kbuild-6.12.41+deb13" + suffix,
    ]

def _action(ctx, config, configuration, inputs, outputs, mnemonic, message):
    python = ctx.attr._python[PythonRuntimeInfo]
    ctx.actions.write(config, json.encode(configuration))
    ctx.actions.run(
        executable = python.interpreter,
        arguments = [ctx.file._runner.path, config.path],
        inputs = depset([config], transitive = [inputs]),
        tools = [ctx.attr._patchelf[DefaultInfo].files_to_run, python.interpreter, ctx.file._runner, ctx.file._architecture] + python.files.to_list(),
        outputs = outputs,
        env = {"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "TZ": "UTC", "PYTHONHASHSEED": "0"},
        mnemonic = mnemonic,
        progress_message = message,
        execution_requirements = {"block-network": "", "no-remote-exec": "1"},
    )


def _kernel_build_impl(ctx):
    architecture = ctx.attr.architecture
    host_architecture = ctx.attr._execution[KernelExecutionInfo].architecture
    kernel_config = kernel_configuration(architecture, ctx.attr._kernel_config[KernelConfigInfo].values, host_architecture)
    raw_files = {name: ctx.actions.declare_file(architecture + "/" + name) for name in ["image", "vmlinux", "System.map", "config", "Module.symvers", "kernel.release"]}
    artifacts = ctx.actions.declare_directory(architecture + "/kernel-artifacts")
    runtime_tree = ctx.actions.declare_directory(architecture + "/runtime-install")
    debug_tree = ctx.actions.declare_directory(architecture + "/debug-install")
    receipt = ctx.actions.declare_file(architecture + "/kernel-build.json")
    config = ctx.actions.declare_file(ctx.label.name + ".action.json")
    source_dir = ctx.file.makefile.dirname
    source_root = source_dir + "/" if source_dir not in ["", "."] else ""
    sources = []
    for src in ctx.files.srcs:
        if not src.path.startswith(source_root):
            fail("kernel inputs must belong to the kernel source directory")
        sources.append({"path": src.path, "name": src.path[len(source_root):]})
    archives = []
    for name, src in [("kernel_dsc", ctx.file.dsc), ("kernel_orig", ctx.file.orig), ("kernel_debian", ctx.file.debian)]:
        source = KERNEL_SOURCES[name]
        archives.append({"path": src.path, "name": source.name, "sha256": source.sha256})
    configuration = {
        "schema": 6, "mode": "compile",
        "architecture": architecture, "host_architecture": host_architecture,
        "recipe_source": ctx.file.makefile.dirname,
        "prepared_source": ctx.file.prepared_makefile.dirname,
        "debian_source": ctx.file.debian_makefile.dirname,
        "kernel_config": kernel_config, "sources": sources, "archives": archives,
        "build_tools": ctx.file.build_tools.path, "patchelf": ctx.executable._patchelf.path,
        "raw_files": {name: file.path for name, file in raw_files.items()},
        "artifacts": artifacts.path, "runtime_tree": runtime_tree.path,
        "debug_tree": debug_tree.path, "receipt": receipt.path,
    }
    inputs = depset(ctx.files.srcs + ctx.files.prepared_sources + ctx.files.debian_sources + [ctx.file.build_tools, ctx.file.dsc, ctx.file.orig, ctx.file.debian])
    _action(ctx, config, configuration, inputs, raw_files.values() + [artifacts, runtime_tree, debug_tree, receipt],
            "SonicKernelBuild", "Compiling SONiC 6.12.41 %s kernel and modules" % architecture.upper())
    return [
        DefaultInfo(files = depset(raw_files.values() + [artifacts])),
        KernelBuildInfo(
            artifacts = artifacts, arch = architecture, host_arch = host_architecture,
            source_root = ctx.file.prepared_makefile.dirname, source_files = depset(ctx.files.prepared_sources),
            build_tools = ctx.file.build_tools, raw_files = raw_files,
            runtime_tree = runtime_tree, debug_tree = debug_tree, receipt = receipt,
            configuration = configuration, inputs = inputs,
        ),
    ]


_kernel_build = rule(
    implementation = _kernel_build_impl,
    attrs = {
        "debian_makefile": attr.label(default = Label("@kernel_debian_prepared//:Makefile"), allow_single_file = True),
        "debian_sources": attr.label_list(default = [Label("@kernel_debian_prepared//:source_files")], allow_files = True),
        "prepared_makefile": attr.label(default = Label("@kernel_prepared//:Makefile"), allow_single_file = True),
        "prepared_sources": attr.label_list(default = [Label("@kernel_prepared//:source_files")], allow_files = True),
        "_execution": attr.label(default = Label("//tools/bazel:kernel_execution"), providers = [KernelExecutionInfo], cfg = "exec"),
        "architecture": attr.string(mandatory = True, values = ["amd64", "arm64"]),
        "srcs": attr.label_list(allow_files = True, mandatory = True),
        "makefile": attr.label(allow_single_file = True, mandatory = True),
        "dsc": attr.label(allow_single_file = True, mandatory = True),
        "orig": attr.label(allow_single_file = True, mandatory = True),
        "debian": attr.label(allow_single_file = True, mandatory = True),
        "build_tools": attr.label(allow_single_file = True, cfg = "exec", mandatory = True),
        "_kernel_config": attr.label(default = Label("//tools/bazel:kernel_config"), providers = [KernelConfigInfo]),
        "_architecture": attr.label(default = Label("//tools/bazel:kernel_arch.py"), allow_single_file = True, cfg = "exec"),
        "_runner": attr.label(default = Label("//tools/bazel:kernel_action.py"), allow_single_file = True, cfg = "exec"),
        "_python": attr.label(default = Label("//tools/bazel:python_runtime"), providers = [PythonRuntimeInfo], cfg = "exec"),
        "_patchelf": attr.label(default = Label("@patchelf//:patchelf"), executable = True, cfg = "exec"),
    },
)


# Script membership comes from Debian's image and headers control templates.
_CONTROL_FILES = {
    "runtime": ["preinst", "postinst", "prerm", "postrm"],
    "debug": [], "headers": ["postinst"], "headers_common": [], "kbuild": [],
}


def _install_impl(ctx):
    kernel = ctx.attr.kernel[KernelBuildInfo]
    prefix = kernel.arch + "/" + ctx.attr.role + "/"
    outputs = {
        "data": ctx.actions.declare_file(prefix + "data.tar"),
        "control_tar": ctx.actions.declare_file(prefix + "control.tar"),
        "control": ctx.actions.declare_file(prefix + "control"),
    }
    controls = {name: ctx.actions.declare_file(prefix + "DEBIAN/" + name) for name in _CONTROL_FILES[ctx.attr.role]}
    if ctx.attr.role == "runtime":
        outputs["boot"] = ctx.actions.declare_directory(kernel.arch + "/boot-files")
        outputs["metadata"] = ctx.actions.declare_file(kernel.arch + "/metadata.json")
    if ctx.attr.role == "debug":
        outputs["debug_validation"] = ctx.actions.declare_file(prefix + "debug-validation.json")
    config = ctx.actions.declare_file(ctx.label.name + ".action.json")
    configuration = dict(kernel.configuration)
    configuration.update({
        "mode": "install", "role": ctx.attr.role,
        "install_outputs": dict({name: file.path for name, file in outputs.items()}, control_files = {name: file.path for name, file in controls.items()}),
    })
    inputs = depset([kernel.artifacts, kernel.receipt] + kernel.raw_files.values() +
                    ([kernel.runtime_tree] if ctx.attr.role in ["runtime", "debug"] else []) +
                    ([kernel.debug_tree] if ctx.attr.role == "debug" else []), transitive = [kernel.inputs])
    _action(ctx, config, configuration, inputs, outputs.values() + controls.values(),
            "SonicKernelInstall", "Installing SONiC %s kernel %s" % (kernel.arch.upper(), ctx.attr.role))
    groups = {name: depset([file]) for name, file in outputs.items()}
    groups.update({"control_" + name: depset([file]) for name, file in controls.items()})
    return [DefaultInfo(files = depset(outputs.values() + controls.values())), KernelInstallInfo(outputs = outputs), OutputGroupInfo(**groups)]


_kernel_install = rule(
    implementation = _install_impl,
    attrs = {
        "kernel": attr.label(providers = [KernelBuildInfo], mandatory = True),
        "role": attr.string(values = ["runtime", "debug", "headers", "headers_common", "kbuild"], mandatory = True),
        "_architecture": attr.label(default = Label("//tools/bazel:kernel_arch.py"), allow_single_file = True, cfg = "exec"),
        "_runner": attr.label(default = Label("//tools/bazel:kernel_action.py"), allow_single_file = True, cfg = "exec"),
        "_python": attr.label(default = Label("//tools/bazel:python_runtime"), providers = [PythonRuntimeInfo], cfg = "exec"),
        "_patchelf": attr.label(default = Label("@patchelf//:patchelf"), executable = True, cfg = "exec"),
    },
)


def _packages_impl(ctx):
    kernel = ctx.attr.kernel[KernelBuildInfo]
    packages = [ctx.file.runtime, ctx.file.debug] + ctx.files.development
    manifest = ctx.actions.declare_file(kernel.arch + "/kernel-packages.json")
    config = ctx.actions.declare_file(ctx.label.name + ".action.json")
    python = ctx.attr._python[PythonRuntimeInfo]
    ctx.actions.write(config, json.encode({"schema": 6, "mode": "manifest", "receipt": kernel.receipt.path,
                                          "packages": [file.path for file in packages], "manifest": manifest.path,
                                          "debug_validation": ctx.attr.debug_install[KernelInstallInfo].outputs["debug_validation"].path}))
    ctx.actions.run(
        executable = python.interpreter,
        arguments = [ctx.file._runner.path, config.path],
        inputs = [config, kernel.receipt, ctx.attr.debug_install[KernelInstallInfo].outputs["debug_validation"]] + packages,
        tools = python.files.to_list() + [python.interpreter, ctx.file._runner, ctx.file._architecture],
        outputs = [manifest], mnemonic = "KernelPackageManifest",
    )
    runtime = ctx.attr.runtime_install[KernelInstallInfo].outputs
    return [
        DefaultInfo(files = depset(packages + [manifest])), kernel,
        OutputGroupInfo(
            runtime = depset([ctx.file.runtime]), debug = depset([ctx.file.debug]),
            development = depset(ctx.files.development), manifest = depset([manifest]),
            artifacts = depset([kernel.artifacts]), runtime_tar = depset([runtime["data"]]),
            control_tar = depset([runtime["control_tar"]]), boot = depset([runtime["boot"]]), metadata = depset([runtime["metadata"]]),
        ),
    ]


_kernel_packages = rule(
    implementation = _packages_impl,
    attrs = {
        "kernel": attr.label(providers = [KernelBuildInfo], mandatory = True),
        "runtime": attr.label(allow_single_file = True, mandatory = True),
        "debug": attr.label(allow_single_file = True, mandatory = True),
        "development": attr.label_list(allow_files = True),
        "runtime_install": attr.label(providers = [KernelInstallInfo], mandatory = True),
        "debug_install": attr.label(providers = [KernelInstallInfo], mandatory = True),
        "_architecture": attr.label(default = Label("//tools/bazel:kernel_arch.py"), allow_single_file = True, cfg = "exec"),
        "_runner": attr.label(default = Label("//tools/bazel:kernel_action.py"), allow_single_file = True, cfg = "exec"),
        "_python": attr.label(default = Label("//tools/bazel:python_runtime"), providers = [PythonRuntimeInfo], cfg = "exec"),
    },
)


def kernel_packages(name, **kwargs):
    """Compile once; install and compress only the package branches requested."""
    common = {key: kwargs[key] for key in ["target_compatible_with", "exec_compatible_with", "visibility", "tags"] if key in kwargs}
    _kernel_build(name = name + "_build", **kwargs)
    debs = {}
    installs = {}
    for role in ["runtime", "debug", "headers", "headers_common", "kbuild"]:
        install = name + "_" + role + "_install"
        installs[role] = ":" + install
        _kernel_install(name = install, kernel = ":" + name + "_build", role = role, **common)
        for output in ["data", "control"] + ["control_" + member for member in _CONTROL_FILES[role]]:
            native.filegroup(name = install + "_" + output, srcs = [":" + install], output_group = output, **{key: value for key, value in common.items() if key != "exec_compatible_with"})
        deb = name + "_" + role + "_deb"
        sonic_deb(name = deb, data = ":" + install + "_data", control = ":" + install + "_control",
                  control_files = {member: ":" + install + "_control_" + member for member in _CONTROL_FILES[role]}, **common)
        debs[role] = ":" + deb
    _kernel_packages(name = name, kernel = ":" + name + "_build", runtime = debs["runtime"], debug = debs["debug"],
                     development = [debs[role] for role in ["headers", "headers_common", "kbuild"]],
                     runtime_install = installs["runtime"], debug_install = installs["debug"], **common)


def _module_impl(ctx):
    kernel = ctx.attr.kernel[KernelBuildInfo]
    prefix = ctx.label.workspace_root + '/' + ctx.label.package
    prefix = prefix.strip('/')
    prefix = prefix + '/' if prefix else ''
    sources = {}
    for source in ctx.files.srcs + [ctx.file.makefile]:
        if not source.path.startswith(prefix):
            fail('Module sources must belong to the module package')
        sources[source.path] = source.path[len(prefix):]
    for key in ctx.attr.make_vars:
        if key in ['M', 'O', 'ARCH', 'CC', 'CROSS_COMPILE', 'HOSTCC', 'HOSTCXX', 'HOSTLD', 'HOSTAR', 'LD', 'AR', 'AS', 'NM', 'OBJCOPY', 'OBJDUMP', 'STRIP', 'READELF', 'CROSS_COMPILE_COMPAT', 'CROSS32_COMPILE', 'KBUILD_EXTRA_SYMBOLS', 'SHELL', 'CONFIG_SHELL']:
            fail('Reserved Kbuild variable: ' + key)
    dependencies = [dep[KernelModuleInfo] for dep in ctx.attr.deps]
    for dep in dependencies:
        if dep.kernel != kernel.artifacts:
            fail('Module dependencies must use the same kernel target')
    modules = ctx.actions.declare_directory(ctx.label.name + '/modules')
    symvers = ctx.actions.declare_file(ctx.label.name + '/Module.symvers')
    order = ctx.actions.declare_file(ctx.label.name + '/modules.order')
    config = ctx.actions.declare_file(ctx.label.name + '.json')
    python = ctx.attr._python[PythonRuntimeInfo]
    ctx.actions.write(config, json.encode({
        'kernel': kernel.artifacts.path,
        'release': kernel.raw_files['kernel.release'].path,
        'source_root': kernel.source_root,
        'host_arch': kernel.host_arch,
        'patchelf': ctx.executable._patchelf.path,
        'arch': kernel.arch,
        'runtime': kernel.build_tools.path,
        'sources': sources,
        'directory': sources[ctx.file.makefile.path].rpartition('/')[0],
        'symbols': [dep.module_symvers.path for dep in dependencies],
        'make_vars': ctx.attr.make_vars,
        'modules': modules.path,
        'metadata': {'Module.symvers': symvers.path, 'modules.order': order.path},
    }))
    ctx.actions.run(
        executable = python.interpreter,
        arguments = [ctx.file._runner.path, config.path],
        inputs = depset(ctx.files.srcs + [ctx.file.makefile, kernel.artifacts, kernel.raw_files['kernel.release'], kernel.build_tools, config] + [dep.module_symvers for dep in dependencies], transitive = [kernel.source_files]),
        tools = python.files.to_list() + [python.interpreter, ctx.file._runner, ctx.attr._patchelf[DefaultInfo].files_to_run],
        outputs = [modules, symvers, order],
        mnemonic = 'SonicKernelModule',
    )
    return [
        DefaultInfo(files = depset([modules, symvers, order])),
        KernelModuleInfo(modules = modules, module_symvers = symvers, kernel = kernel.artifacts),
        OutputGroupInfo(modules = depset([modules]), Module_symvers = depset([symvers]), modules_order = depset([order])),
    ]

kernel_module = rule(
    implementation = _module_impl,
    attrs = {
        'kernel': attr.label(mandatory = True, providers = [KernelBuildInfo]),
        'srcs': attr.label_list(allow_files = True),
        'makefile': attr.label(mandatory = True, allow_single_file = True),
        'deps': attr.label_list(providers = [KernelModuleInfo]),
        'make_vars': attr.string_dict(),
        '_patchelf': attr.label(default = Label('@patchelf//:patchelf'), executable = True, cfg = 'exec'),
        '_python': attr.label(default = Label('//tools/bazel:python_runtime'), cfg = 'exec', providers = [PythonRuntimeInfo]),
        '_runner': attr.label(default = Label('//tools/bazel:module_action.py'), cfg = 'exec', allow_single_file = True),
    },
)


def _output_impl(ctx):
    kernel = ctx.attr.kernel[KernelBuildInfo]
    return [DefaultInfo(files = depset([kernel.raw_files[ctx.attr.path]]))]

kernel_output = rule(
    implementation = _output_impl,
    attrs = {
        'kernel': attr.label(mandatory = True, providers = [KernelBuildInfo]),
        'path': attr.string(mandatory = True),
    },
)


def _metadata_impl(ctx):
    output = ctx.actions.declare_file(ctx.label.name + '.json')
    tree = ctx.actions.declare_directory(ctx.label.name + '.packages')
    spec = ctx.actions.declare_file(ctx.label.name + '.inputs.json')
    python = ctx.attr._python[PythonRuntimeInfo]
    ctx.actions.write(spec, json.encode({
        'runtime': ctx.file.runtime.path,
        'control': ctx.file.control.path,
        'runtime_target': str(ctx.attr.runtime.label),
        'package': _packages(ctx.attr.kernel[KernelBuildInfo].arch)[0].split('_')[0],
        'architecture': ctx.attr.kernel[KernelBuildInfo].arch,
        'output': output.path,
        'tree': tree.path,
    }))
    ctx.actions.run(
        executable = python.interpreter,
        arguments = [ctx.file._runner.path, spec.path],
        inputs = [spec, ctx.file.runtime, ctx.file.control],
        tools = python.files.to_list() + [python.interpreter, ctx.file._runner],
        outputs = [output, tree],
        mnemonic = 'KernelRuntimeMetadata',
    )
    return [DefaultInfo(files = depset([output])), RuntimePackagesInfo(metadata = output, trees = depset([tree]))]

kernel_runtime_metadata = rule(
    implementation = _metadata_impl,
    attrs = {
        'runtime': attr.label(mandatory = True, allow_single_file = True),
        'control': attr.label(mandatory = True, allow_single_file = True),
        'kernel': attr.label(mandatory = True, providers = [KernelBuildInfo]),
        '_python': attr.label(default = Label('//tools/bazel:python_runtime'), cfg = 'exec', providers = [PythonRuntimeInfo]),
        '_runner': attr.label(default = Label('//tools/bazel:runtime_metadata.py'), cfg = 'exec', allow_single_file = True),
    },
)
