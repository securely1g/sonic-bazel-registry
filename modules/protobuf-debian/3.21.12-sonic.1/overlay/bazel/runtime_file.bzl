"""Select the declared dynamic library file for native contract tests."""

load("@rules_cc//cc/common:cc_info.bzl", "CcInfo")

def _runtime_file_impl(ctx):
    files = {}
    for linker_input in ctx.attr.library[CcInfo].linking_context.linker_inputs.to_list():
        libraries = linker_input.libraries
        for library in libraries.to_list() if type(libraries) == "depset" else libraries:
            file = library.resolved_symlink_dynamic_library or library.dynamic_library
            if file != None and file.basename == ctx.attr.basename:
                files[file.path] = file
    if len(files) != 1:
        fail("Expected one {} dynamic library, found {}".format(ctx.attr.basename, files.keys()))
    return [DefaultInfo(files = depset(files.values()))]

runtime_file = rule(
    implementation = _runtime_file_impl,
    attrs = {
        "library": attr.label(mandatory = True, providers = [CcInfo]),
        "basename": attr.string(mandatory = True),
    },
)
