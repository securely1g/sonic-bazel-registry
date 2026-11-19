"""Launch build-time generators with their declared execution-platform runtime."""

load("@rules_cc//cc/common:cc_info.bzl", "CcInfo")

def _key(ctx, file):
    return file.short_path[3:] if file.short_path.startswith("../") else ctx.workspace_name + "/" + file.short_path

def _impl(ctx):
    files = [ctx.file.binary]
    for target in ctx.attr.runtime:
        files.extend(target[DefaultInfo].files.to_list())
    for dep in ctx.attr.deps:
        for linker_input in dep[CcInfo].linking_context.linker_inputs.to_list():
            for library in linker_input.libraries:
                if library.dynamic_library:
                    files.append(library.dynamic_library)
                if library.resolved_symlink_dynamic_library:
                    files.append(library.resolved_symlink_dynamic_library)
    loaders = [file for file in files if file.basename in ["ld-linux-x86-64.so.2", "ld-linux-aarch64.so.1"]]
    if not loaders:
        fail("The declared code-generator runtime must include its dynamic loader")
    directories = {_key(ctx, file).rpartition("/")[0]: True for file in files if ".so" in file.basename}
    executable = ctx.actions.declare_file(ctx.label.name)
    loader = _key(ctx, loaders[0])
    ctx.actions.write(executable, """#!/bin/bash
set -euo pipefail
rf="$0.runfiles"
if [[ ! -f "$rf/{loader}" ]]; then rf="${{RUNFILES_DIR:-}}"; fi
if [[ -z "$rf" || ! -f "$rf/{loader}" ]]; then
  echo "P4C code-generator runfiles are missing: $rf" >&2
  exit 1
fi
rf="$(cd "$rf" && pwd)"
exec "$rf/{loader}" --inhibit-cache --library-path "{libraries}" "$rf/{binary}" "$@"
""".format(
        loader = loader,
        libraries = ":".join(["$rf/" + directory for directory in directories]),
        binary = _key(ctx, ctx.file.binary),
    ), is_executable = True)
    runfiles = ctx.runfiles(files = files)
    for target in ctx.attr.runtime + ctx.attr.deps + [ctx.attr.binary]:
        runfiles = runfiles.merge(target[DefaultInfo].default_runfiles)
    return [DefaultInfo(executable = executable, runfiles = runfiles)]

# rules_foreign_cc's build_data transitions the entire generator dependency
# graph to cfg="exec", including CMake, GCC and these runtime dependencies.
p4c_codegen = rule(
    implementation = _impl,
    executable = True,
    attrs = {
        "binary": attr.label(allow_single_file = True, mandatory = True),
        "runtime": attr.label_list(),
        "deps": attr.label_list(providers = [CcInfo]),
    },
)
