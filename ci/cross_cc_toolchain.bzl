"""Legacy C++ adapter compatible with the tested consumer's existing rules_cc.

Only compiler/sysroot repository files are used. No host compiler, headers, or
libraries are substituted for the separately pinned Debian provider inputs.
"""

load("@bazel_tools//tools/cpp:cc_toolchain_config_lib.bzl", "action_config", "feature", "flag_group", "flag_set", "tool", "tool_path")

def _impl(ctx):
    compiler = ctx.file.compiler_anchor.path[:-len("/inputs.json")]
    sysroot = ctx.file.sysroot_anchor.path[:-len("/usr/include/features.h")]
    c_actions = ["c-compile", "preprocess-assemble", "assemble"]
    cxx_actions = ["c++-compile", "c++-header-parsing", "c++-module-compile", "c++-module-codegen"]
    includes = [
        sysroot + "/usr/lib/gcc/aarch64-linux-gnu/14/include",
        sysroot + "/usr/include/aarch64-linux-gnu",
        sysroot + "/usr/include",
    ]
    cxx_includes = [
        sysroot + "/usr/include/c++/14",
        sysroot + "/usr/include/aarch64-linux-gnu/c++/14",
        sysroot + "/usr/include/c++/14/backward",
    ]
    link_actions = [
        "c++-link-executable",
        "c++-link-dynamic-library",
        "c++-link-nodeps-dynamic-library",
        "lto-index-for-executable",
        "lto-index-for-dynamic-library",
        "lto-index-for-nodeps-dynamic-library",
    ]
    # Bazel 8.5.1's generated legacy link actions imply strip_debug_symbols,
    # preventing callers such as foreign_cc from disabling it. Preserve the
    # other CppActionConfigs link implications, but make stripping an ordinary
    # default-enabled feature that honors the caller's disabled features.
    link_implications = [
        "linkstamps",
        "output_execpath_flags",
        "runtime_library_search_directories",
        "library_search_directories",
        "libraries_to_link",
        "user_link_flags",
        "legacy_link_flags",
        "linker_param_file",
        "fission_support",
        "sysroot",
    ]
    # foreign_cc uses the C++ compile action's driver as CXX when it configures
    # and links. G++ adds its runtime after the input objects, including when
    # Autoconf puts LDFLAGS before a probe source. Keep Bazel 8's compile flags.
    cxx_compile = action_config(
        action_name = "c++-compile",
        enabled = True,
        tools = [tool(path = "aarch64-linux-gnu-g++")],
        implies = [
            "legacy_compile_flags",
            "user_compile_flags",
            "sysroot",
            "unfiltered_compile_flags",
            "compiler_input_flags",
            "compiler_output_flags",
        ],
    )
    return cc_common.create_cc_toolchain_config_info(
        ctx = ctx,
        toolchain_identifier = "registry-ci-aarch64-gcc14",
        host_system_name = "x86_64-linux-gnu",
        target_system_name = "aarch64-linux-gnu",
        target_cpu = "aarch64",
        target_libc = "glibc",
        compiler = "gcc",
        abi_version = "aarch64",
        abi_libc_version = "glibc",
        builtin_sysroot = sysroot,
        cxx_builtin_include_directories = cxx_includes + includes,
        tool_paths = [
            tool_path(name = "gcc", path = "aarch64-linux-gnu-gcc"),
            tool_path(name = "cpp", path = "aarch64-linux-gnu-gcc"),
        ] + [tool_path(name = name, path = "compiler/bin/aarch64-linux-gnu-" + name)
             for name in ["ld", "ar", "nm", "objcopy", "objdump", "strip"]] + [
            tool_path(name = "gcov", path = "compiler/usr/bin/aarch64-linux-gnu-gcov-14"),
        ],
        action_configs = [cxx_compile] + [
            action_config(
                action_name = action,
                enabled = True,
                tools = [tool(path = "aarch64-linux-gnu-gcc")],
                implies = link_implications + (
                    ["build_interface_libraries", "dynamic_library_linker_tool", "shared_flag"]
                    if "dynamic-library" in action else ["force_pic_flags"]
                ),
            )
            for action in link_actions
        ],
        features = [
            feature(name = "supports_pic", enabled = True),
            feature(name = "supports_dynamic_linker", enabled = True),
            feature(name = "strip_debug_symbols", enabled = True, flag_sets = [flag_set(
                actions = link_actions,
                flag_groups = [flag_group(flags = ["-Wl,-S"], expand_if_available = "strip_debug_symbols")],
            )]),
            # C++ headers use include_next to find the C headers, so they must
            # precede the target libc include directories.
            feature(name = "ci_cxx", enabled = True, flag_sets = [flag_set(
                actions = cxx_actions,
                flag_groups = [flag_group(flags = ["-nostdinc++"] + [arg for directory in cxx_includes for arg in ["-isystem", directory]])],
            )]),
            feature(name = "ci_compile", enabled = True, flag_sets = [flag_set(
                actions = c_actions + cxx_actions,
                flag_groups = [flag_group(flags = ["-nostdinc", "-fno-canonical-system-headers"] + [arg for directory in includes for arg in ["-isystem", directory]])],
            )]),
            feature(name = "ci_link", enabled = True, flag_sets = [flag_set(
                actions = ["c++-link-executable", "c++-link-dynamic-library", "c++-link-nodeps-dynamic-library"],
                flag_groups = [flag_group(flags = [
                    "-B" + sysroot + "/usr/lib/gcc/aarch64-linux-gnu/14/",
                    "-B" + sysroot + "/usr/lib/aarch64-linux-gnu/",
                    "-L" + sysroot + "/usr/lib/gcc/aarch64-linux-gnu/14",
                    "-L" + sysroot + "/usr/lib/aarch64-linux-gnu",
                    "-lstdc++", "-lm",
                ])],
            )]),
        ],
    )

linux_aarch64_gcc = rule(
    implementation = _impl,
    attrs = {
        "compiler_anchor": attr.label(allow_single_file = True),
        "sysroot_anchor": attr.label(allow_single_file = True),
    },
    provides = [CcToolchainConfigInfo],
)
