"""A fixture-only GCC toolchain using caller-supplied compiler and sysroot files."""
load("@rules_cc//cc:defs.bzl", "cc_common")
load("@rules_cc//cc:cc_toolchain_config_lib.bzl", "feature", "flag_group", "flag_set", "tool_path")
load("@rules_cc//cc:action_names.bzl", "ACTION_NAMES")

def _impl(ctx):
    compile_actions = [ACTION_NAMES.c_compile, ACTION_NAMES.cpp_compile, ACTION_NAMES.assemble, ACTION_NAMES.preprocess_assemble]
    link_actions = [ACTION_NAMES.cpp_link_executable, ACTION_NAMES.cpp_link_dynamic_library, ACTION_NAMES.cpp_link_nodeps_dynamic_library]
    sysroot = ctx.file.sysroot_marker.path.removesuffix("/usr/include/stdio.h")
    gcc_lib = sysroot + "/usr/lib/gcc/aarch64-linux-gnu/" + ctx.attr.gcc_version
    compiler_flags = ["--sysroot=" + sysroot, "-fPIC", "-isystem", sysroot + "/usr/include/aarch64-linux-gnu", "-isystem", gcc_lib + "/include"]
    linker_flags = ["--sysroot=" + sysroot, "-B" + sysroot + "/usr/lib/aarch64-linux-gnu/", "-B" + gcc_lib + "/", "-L" + gcc_lib]
    return [cc_common.create_cc_toolchain_config_info(
        ctx = ctx,
        toolchain_identifier = "fixture_aarch64_gcc",
        host_system_name = "local",
        target_system_name = "aarch64-linux-gnu",
        target_cpu = "aarch64",
        target_libc = "glibc",
        compiler = "gcc",
        abi_version = "aarch64",
        abi_libc_version = "glibc",
        builtin_sysroot = sysroot,
        cxx_builtin_include_directories = ["%sysroot%/usr/include", "%sysroot%/usr/include/aarch64-linux-gnu", "%sysroot%/usr/lib/gcc/aarch64-linux-gnu/" + ctx.attr.gcc_version + "/include"],
        tool_paths = [tool_path(name = name, path = ctx.file.compiler.dirname + "/" + ctx.file.compiler.basename.removesuffix("gcc") + executable) for name, executable in [
            ("gcc", "gcc"), ("ld", "ld"), ("ar", "ar"), ("nm", "nm"), ("objdump", "objdump"), ("strip", "strip"), ("dwp", "ar"), ("cpp", "gcc"), ("gcov", "gcc"),
        ]],
        features = [
            feature(name = "supports_pic", enabled = True),
            feature(name = "supports_dynamic_linker", enabled = True),
            feature(name = "supports_interface_shared_libraries", enabled = True),
            feature(name = "fixture_compile", enabled = True, flag_sets = [flag_set(actions = compile_actions, flag_groups = [flag_group(flags = compiler_flags)])]),
            feature(name = "fixture_link", enabled = True, flag_sets = [flag_set(actions = link_actions, flag_groups = [flag_group(flags = linker_flags)])]),
        ],
    )]

cross_config = rule(implementation = _impl, provides = [CcToolchainConfigInfo], attrs = {
    "compiler": attr.label(allow_single_file = True, mandatory = True),
    "sysroot_marker": attr.label(allow_single_file = True, mandatory = True),
    "gcc_version": attr.string(mandatory = True),
})
