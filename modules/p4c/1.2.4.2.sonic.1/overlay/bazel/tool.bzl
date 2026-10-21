"""Run P4C with its declared libraries, preprocessor and P4 include files."""
load("@rules_cc//cc/common:cc_info.bzl", "CcInfo")

def _key(ctx, file):
    return file.short_path[3:] if file.short_path.startswith("../") else ctx.workspace_name + "/" + file.short_path

def _impl(ctx):
    files = [ctx.file.binary, ctx.file.cpp] + ctx.files.data
    for target in ctx.attr.runtime:
        files.extend(target[DefaultInfo].files.to_list())
    for dep in ctx.attr.deps:
        for input in dep[CcInfo].linking_context.linker_inputs.to_list():
            for lib in input.libraries:
                if lib.dynamic_library:
                    files.append(lib.dynamic_library)
                if lib.resolved_symlink_dynamic_library:
                    files.append(lib.resolved_symlink_dynamic_library)
    loaders = [f for f in files if f.basename in ["ld-linux-x86-64.so.2", "ld-linux-aarch64.so.1"]]
    if not loaders:
        fail("The declared GCC runtime does not expose the dynamic loader")
    include = [f for f in ctx.files.data if f.basename == "core.p4"][0]
    directories = { _key(ctx, f).rpartition("/")[0]: True for f in files if ".so" in f.basename }
    header = """#!/bin/bash
set -euo pipefail
rf="${RUNFILES_DIR:-$0.runfiles}"
if [[ ! -d "$rf" ]]; then echo "P4C runfiles are missing: $rf" >&2; exit 1; fi
rf="$(cd "$rf" && pwd)"
export RUNFILES_DIR="$rf"
"""
    cpp = ctx.actions.declare_file(ctx.label.name + ".tools/cpp")
    ctx.actions.write(cpp, header + 'exec "$rf/' + _key(ctx, ctx.file.cpp) + '" -E "$@"\n', is_executable = True)
    script = ctx.actions.declare_file(ctx.label.name)
    ctx.actions.write(script, header + '\n'.join([
        'export PATH="$rf/' + _key(ctx, cpp).rpartition("/")[0] + ':$PATH"',
        'export P4C_16_INCLUDE_PATH="$rf/' + _key(ctx, include).rpartition("/")[0] + '"',
        'exec "$rf/' + _key(ctx, loaders[0]) + '" --inhibit-cache --library-path "' + ':'.join(['$rf/' + path for path in directories]) + '" "$rf/' + _key(ctx, ctx.file.binary) + '" "$@"',
        "",
    ]), is_executable = True)
    runfiles = ctx.runfiles(files = files + [cpp])
    for dep in ctx.attr.runtime + ctx.attr.deps + [ctx.attr.binary, ctx.attr.cpp]:
        runfiles = runfiles.merge(dep[DefaultInfo].default_runfiles)
    return [DefaultInfo(executable = script, runfiles = runfiles)]

p4c_tool = rule(
    implementation = _impl,
    executable = True,
    attrs = {
        "binary": attr.label(allow_single_file = True, mandatory = True),
        "cpp": attr.label(allow_single_file = True, mandatory = True),
        "runtime": attr.label_list(),
        "data": attr.label_list(allow_files = True),
        "deps": attr.label_list(providers = [CcInfo]),
    },
)
