"""CPython's original static profile workload and native GCC stages."""
load("@rules_cc//cc:cc_library.bzl", "cc_library")
load("@rules_cc//cc:action_names.bzl", "ACTION_NAMES")
load("@rules_cc//cc/common:cc_common.bzl", "cc_common")
load("@rules_cc//cc:find_cc_toolchain.bzl", "find_cpp_toolchain", "use_cc_toolchain")
load("@rules_cc//cc/common:cc_info.bzl", "CcInfo")

_GENERATE = "-fprofile-generate=."

# debian/rules enables PGO only when DEB_HOST_GNU_TYPE == DEB_BUILD_GNU_TYPE.
_ExecutionCompiler = provider(fields = ["cpu"])

def _execution_compiler_impl(ctx):
    return [_ExecutionCompiler(cpu = find_cpp_toolchain(ctx).cpu)]

execution_compiler = rule(
    implementation = _execution_compiler_impl,
    toolchains = use_cc_toolchain(),
    fragments = ["cpp"],
)

def _native_profile(ctx):
    return find_cpp_toolchain(ctx).cpu == ctx.attr._execution_compiler[_ExecutionCompiler].cpu

def _profile_flags_impl(ctx):
    flags = []
    if _native_profile(ctx):
        if ctx.attr.stage == "generate":
            flags = [_GENERATE]
        else:
            flags = ["-fprofile-use=" + ctx.file.profile.path, "-fprofile-correction"]
    output = ctx.actions.declare_file(ctx.label.name + ".rsp")
    ctx.actions.write(output, "\n".join(flags) + "\n")
    return [DefaultInfo(files = depset([output]))]

profile_flags = rule(
    implementation = _profile_flags_impl,
    attrs = {
        "stage": attr.string(mandatory = True, values = ["generate", "use"]),
        "profile": attr.label(allow_single_file = True),
        "_execution_compiler": attr.label(default = Label("//python:execution_compiler"), cfg = "exec"),
    },
    toolchains = use_cc_toolchain(),
    fragments = ["cpp"],
)

def profile_objects(name, srcs, namespace, stage, profile = None, copts = [], **kwargs):
    """Keep native cc actions; group only to preserve logical source parents."""
    groups = {}
    headers = []
    for source in srcs:
        if any([source.endswith(ext) for ext in [".c", ".cc", ".cpp", ".S", ".s"]]) or source == ":builtin_table":
            parent = "Modules" if source == ":builtin_table" else source.rsplit("/", 1)[0]
            key = "Python_sysmodule" if source == "Python/sysmodule.c" else parent
            groups.setdefault(key, []).append(source)
        else:
            headers.append(source)
    children = []
    for parent in sorted(groups):
        child = name + "_" + parent.replace("/", "_")
        logical_parent = "Python" if parent == "Python_sysmodule" else parent
        flags = copts + ["-dumpdir", "/sonic-fips-cpython-pgo/" + namespace + "/" + logical_parent + "/"]
        child_kwargs = dict(kwargs)
        if parent == "Python_sysmodule":
            child_kwargs["local_defines"] = kwargs.get("local_defines", []) + ["ABIFLAGS='\"\"'"]
        inputs = []
        profile_flags(name = child + "_profile_flags", stage = stage, profile = profile if stage == "use" else None)
        flags += ["@$(location :" + child + "_profile_flags)"]
        inputs = [":" + child + "_profile_flags"] + ([profile] if stage == "use" else [])
        cc_library(
            name = child,
            srcs = groups[parent] + headers,
            copts = flags,
            additional_compiler_inputs = inputs,
            alwayslink = True,
            **child_kwargs
        )
        children.append(":" + child)
    return children

def _freeze_impl(ctx):
    header = ctx.actions.declare_file(ctx.attr.header)
    profile = ctx.actions.declare_directory(ctx.label.name + ".gcda")
    args = ctx.actions.args()
    args.add_all([ctx.file._driver.path, "freeze", ctx.executable.tool.path, ctx.attr.module, ctx.file.src.path, header.path, profile.path])
    ctx.actions.run(
        executable = ctx.executable._python,
        arguments = [args],
        tools = [ctx.attr.tool[DefaultInfo].files_to_run, ctx.attr._python[DefaultInfo].files_to_run],
        inputs = [ctx.file.src, ctx.file._driver],
        outputs = [header, profile],
        mnemonic = "CPythonProfileFreeze",
        env = {"LANG": "C", "LC_ALL": "C", "TZ": "UTC"},
    )
    return [DefaultInfo(files = depset([header])), OutputGroupInfo(profiles = depset([profile]))]

profile_freeze = rule(
    implementation = _freeze_impl,
    attrs = {
        "tool": attr.label(executable = True, cfg = "exec", mandatory = True),
        "src": attr.label(allow_single_file = True, mandatory = True),
        "module": attr.string(mandatory = True),
        "header": attr.string(mandatory = True),
        "_driver": attr.label(default = Label("//python:profile_driver.py"), allow_single_file = True),
        "_python": attr.label(default = Label("@sonic_build_infra//tools/build_tools:python3"), executable = True, cfg = "exec"),
    },
)

def _profile_impl(ctx):
    tc = find_cpp_toolchain(ctx)
    if not _native_profile(ctx):
        output = ctx.actions.declare_directory(ctx.label.name + ".gcda")
        report = ctx.actions.declare_file(ctx.label.name + ".json")
        ctx.actions.run(executable = ctx.executable._python, arguments = ["-c", "import os,sys;os.makedirs(sys.argv[1],exist_ok=True)", output.path], outputs = [output], tools = [ctx.attr._python[DefaultInfo].files_to_run], mnemonic = "CPythonCrossWithoutPGO")
        ctx.actions.write(report, json.encode({"pgo_enabled": False, "reason": "original DEB_HOST_GNU_TYPE differs from DEB_BUILD_GNU_TYPE", "target_cpu": tc.cpu, "execution_cpu": ctx.attr._execution_compiler[_ExecutionCompiler].cpu}) + "\n")
        return [DefaultInfo(files = depset([output])), OutputGroupInfo(report = depset([report]))]
    features = cc_common.configure_features(ctx = ctx, cc_toolchain = tc, requested_features = ctx.features, unsupported_features = ctx.disabled_features)
    contexts = [dep[CcInfo].compilation_context for dep in ctx.attr.compiler_deps]
    compiler_headers = depset(transitive = [c.headers for c in contexts])
    compile_context = {
        "feature_configuration": features,
        "cc_toolchain": tc,
        "include_directories": depset(transitive = [c.includes for c in contexts]),
        "quote_include_directories": depset(transitive = [c.quote_includes for c in contexts]),
        "system_include_directories": depset(transitive = [c.system_includes for c in contexts] + [c.external_includes for c in contexts]),
        # Library pkg-config defines belong to their module-local recipes,
        # not to the global CC used by configure and third-party extensions.
        # Global preprocessing flags remain those selected by the toolchain.
    }
    compilers = {}
    for name, action in [("CC", ACTION_NAMES.c_compile), ("CXX", ACTION_NAMES.cpp_compile)]:
        variables = cc_common.create_compile_variables(user_compile_flags = ctx.fragments.cpp.copts + (ctx.fragments.cpp.conlyopts if name == "CC" else ctx.fragments.cpp.cxxopts), **compile_context)
        compilers[name] = [cc_common.get_tool_for_action(feature_configuration = features, action_name = action)] + cc_common.get_memory_inefficient_command_line(feature_configuration = features, action_name = action, variables = variables)
    link_variables = cc_common.create_link_variables(feature_configuration = features, cc_toolchain = tc, is_linking_dynamic_library = False)
    link_flags = cc_common.get_memory_inefficient_command_line(feature_configuration = features, action_name = ACTION_NAMES.cpp_link_executable, variables = link_variables)
    output = ctx.actions.declare_directory(ctx.label.name + ".gcda")
    report = ctx.actions.declare_file(ctx.label.name + ".json")
    runtime_files = ctx.attr._runtime[DefaultInfo].default_runfiles.files.to_list()
    loaders = [f for f in runtime_files if f.basename.startswith("ld-linux-")]
    if len(loaders) != 1:
        fail("CPython profile needs exactly one declared target loader")
    toolchain_files = tc.all_files.to_list()
    gcov = [f for f in toolchain_files if "gcov-tool" in f.basename and "/usr/bin/" in f.path]
    if len(gcov) != 1:
        fail("CPython profile needs the selected GCC's unique gcov-tool")
    # Modern feature-selected tools are authoritative; the compatibility
    # CcToolchainInfo.compiler_executable field need not name the active driver.
    compiler = compilers["CC"][0]
    manifests = [f for f in toolchain_files if f.basename == "inputs.json" and compiler.startswith(f.dirname + "/bin/")]
    if len(manifests) != 1:
        fail("CPython profile needs declared GCC execution metadata for " + compiler + "; candidates=" + str([f.path for f in toolchain_files if f.basename == "inputs.json"]))
    files = [ctx.file._execution_tools] + ctx.files.srcs + ctx.files.freeze_profiles + ctx.files.runtime_payloads + runtime_files + [ctx.file._driver, ctx.file.metadata, ctx.file.makefile, ctx.file.pyconfig, ctx.file.source_marker, ctx.file.setup_local]
    directories = {f.dirname: True for f in runtime_files}
    modules = {}
    for name, target in ctx.attr.modules.items():
        outputs = target[DefaultInfo].files.to_list()
        if len(outputs) != 1:
            fail("Expected one CPython extension for " + name)
        modules[name] = outputs[0].path
        files.extend(outputs)
        files.extend(target[DefaultInfo].default_runfiles.files.to_list())
    compiler_directories = {}
    for target in ctx.attr.compiler_deps:
        for item in target[CcInfo].linking_context.linker_inputs.to_list():
            files.extend(item.additional_inputs)
            for file in item.additional_inputs:
                if file.basename.endswith(".a") or file.basename.endswith(".so") or ".so." in file.basename:
                    compiler_directories[file.dirname] = True
            for library in item.libraries:
                for file in [library.dynamic_library, library.resolved_symlink_dynamic_library, library.static_library, library.pic_static_library, library.interface_library]:
                    if file:
                        files.append(file)
                        compiler_directories[file.dirname] = True
    for target in ctx.attr.runtime_deps:
        for item in target[CcInfo].linking_context.linker_inputs.to_list():
            files.extend(item.additional_inputs)
            for library in item.libraries:
                for file in [library.dynamic_library, library.resolved_symlink_dynamic_library]:
                    if file:
                        files.append(file)
                        directories[file.dirname] = True
    for target in [ctx.attr.interpreter, ctx.attr.embed]:
        if target:
            files.extend(target[DefaultInfo].default_runfiles.files.to_list())
    openssl_libraries = {}
    for name, target in ctx.attr.openssl_libraries.items():
        candidates = []
        for item in target[CcInfo].linking_context.linker_inputs.to_list():
            for library in item.libraries:
                for file in [library.resolved_symlink_dynamic_library or library.dynamic_library]:
                    if file and file.basename.startswith("lib" + name + ".so."):
                        candidates.append(file)
        candidates = depset(candidates).to_list()
        if len(candidates) != 1:
            fail("Expected one declared OpenSSL SONAME for " + name + ": " + str([f.path for f in candidates]))
        openssl_libraries[name] = candidates[0].path
        files.extend(candidates)
    files.extend(ctx.files.openssl_pkgconfig)
    spec = ctx.actions.declare_file(ctx.label.name + ".spec.json")
    spec_data = {
        "interpreter": ctx.executable.interpreter.path,
        "embed": ctx.executable.embed.path if ctx.attr.embed else None,
        "source_root": ctx.file.source_marker.dirname.rsplit("/", 1)[0],
        "setup_local": ctx.file.setup_local.path,
        "source_files": [f.path for f in ctx.files.srcs],
        "metadata": ctx.file.metadata.path,
        "makefile": ctx.file.makefile.path,
        "pyconfig": ctx.file.pyconfig.path,
        "modules": modules,
        "loader": loaders[0].path,
        "library_directories": sorted(directories),
        "target_runtime_directories": sorted({f.dirname: True for f in runtime_files}),
        "gcc_metadata": manifests[0].path,
        "gcov_tool": gcov[0].path,
        "freeze_profiles": [f.path for f in ctx.files.freeze_profiles],
        "runtime_payloads": [f.path for f in ctx.files.runtime_payloads],
        "workload": ctx.attr.workload,
        "patchelf": ctx.executable._patchelf.path,
        "shell": ctx.file._execution_tools.path + "/bin/sh",
        "execution_path": ctx.file._execution_tools.path + "/bin:" + compiler.rsplit("/", 1)[0],
        "compilers": compilers,
        "link_flags": link_flags,
        "compiler_library_directories": sorted(compiler_directories),
        "build_configuration": ctx.attr.build_configuration,
        "configure_environment": ctx.attr.configure_environment,
        "openssl_pkgconfig": [f.path for f in ctx.files.openssl_pkgconfig],
        "openssl_libraries": openssl_libraries,
        "pkgconf": ctx.executable._pkgconf.path,
    }
    if ctx.attr.workload == "original":
        if not ctx.file.test_data_runtime:
            fail("Original CPython workloads require the declared Python test data runtime")
        spec_data["test_data_runtime"] = ctx.file.test_data_runtime.path
        files += ctx.files.test_data_runtime
    action_tools = [ctx.attr._pkgconf[DefaultInfo].files_to_run, ctx.attr._python[DefaultInfo].files_to_run, ctx.attr._patchelf[DefaultInfo].files_to_run]
    ctx.actions.write(spec, json.encode(spec_data) + "\n")
    files += [ctx.executable.interpreter, spec]
    if ctx.attr.embed:
        files.append(ctx.executable.embed)
    ctx.actions.run(
        executable = ctx.executable._python,
        arguments = [ctx.file._driver.path, "profile", spec.path, output.path, report.path],
        inputs = depset(files, transitive = [tc.all_files, compiler_headers]),
        tools = action_tools,
        outputs = [output, report],
        mnemonic = "CPythonProfileTask",
        env = {"LANG": "C", "LC_ALL": "C", "TZ": "UTC", "TEST_TMPDIR": "/tmp"},
    )
    return [DefaultInfo(files = depset([output])), OutputGroupInfo(report = depset([report]), spec = depset([spec]))]

python_profile = rule(
    implementation = _profile_impl,
    attrs = {
        "_execution_compiler": attr.label(default = Label("//python:execution_compiler"), cfg = "exec"),
        "interpreter": attr.label(executable = True, cfg = "target", mandatory = True),
        "embed": attr.label(executable = True, cfg = "target"),
        "modules": attr.string_keyed_label_dict(mandatory = True),
        "srcs": attr.label_list(allow_files = True),
        "source_marker": attr.label(allow_single_file = True, mandatory = True),
        "setup_local": attr.label(default = Label("//python:original_setup_local"), allow_single_file = True),
        "metadata": attr.label(allow_single_file = True, mandatory = True),
        "makefile": attr.label(allow_single_file = True, mandatory = True),
        "pyconfig": attr.label(allow_single_file = True, mandatory = True),
        "runtime_deps": attr.label_list(providers = [CcInfo]),
        "compiler_deps": attr.label_list(providers = [CcInfo]),
        "build_configuration": attr.string_dict(),
        "configure_environment": attr.string_dict(),
        "openssl_pkgconfig": attr.label_list(allow_files = True),
        "openssl_libraries": attr.string_keyed_label_dict(providers = [CcInfo]),
        "_pkgconf": attr.label(default = Label("@sonic_build_infra//tools/build_tools:pkgconf"), executable = True, cfg = "exec"),
        "runtime_payloads": attr.label_list(allow_files = True),
        "test_data_runtime": attr.label(allow_single_file = True, cfg = "exec"),
        "freeze_profiles": attr.label_list(allow_files = True),
        "workload": attr.string(default = "original", values = ["original", "contextvars-smoke"]),
        "_driver": attr.label(default = Label("//python:profile_driver.py"), allow_single_file = True),
        "_patchelf": attr.label(default = Label("@sonic_build_infra//tools/build_tools:patchelf"), executable = True, cfg = "exec"),
        "_execution_tools": attr.label(default = Label("@sonic_build_infra//tools/build_tools:kernel_runtime"), allow_single_file = True, cfg = "exec"),
        "_runtime": attr.label(default = Label("@sonic_build_infra//tools/build_tools:source_runtime"), cfg = "exec"),
        "_python": attr.label(default = Label("@sonic_build_infra//tools/build_tools:python3"), executable = True, cfg = "exec"),
    },
    fragments = ["cpp"],
    toolchains = use_cc_toolchain(),
)

def _empty_impl(ctx):
    directory = ctx.actions.declare_directory(ctx.label.name + ".gcda")
    ctx.actions.run(
        executable = ctx.executable._python,
        arguments = ["-c", "from pathlib import Path; import sys; Path(sys.argv[1]).mkdir(parents=True, exist_ok=True)", directory.path],
        outputs = [directory],
        tools = [ctx.attr._python[DefaultInfo].files_to_run],
    )
    return [DefaultInfo(files = depset([directory]))]

empty_profile = rule(implementation = _empty_impl, attrs = {
    "_python": attr.label(default = Label("@sonic_build_infra//tools/build_tools:python3"), executable = True, cfg = "exec"),
})
