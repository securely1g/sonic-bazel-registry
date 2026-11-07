"""Materialize declared target headers and libraries with upstream BSD tar."""

_TAR = "@tar.bzl//tar/toolchain:type"

def _impl(ctx):
    output = ctx.actions.declare_directory(ctx.label.name)
    toolchain = ctx.toolchains[_TAR]
    args = ctx.actions.args()
    args.add(toolchain.tarinfo.binary)
    args.add(output.path)
    args.add_all(ctx.files.archives)
    ctx.actions.run(
        executable = ctx.executable._unpack,
        arguments = [args],
        inputs = ctx.files.archives,
        tools = toolchain.default.files,
        outputs = [output],
        mnemonic = "LldpdTargetLibraries",
    )
    return [DefaultInfo(files = depset([output]))]

target_libraries = rule(
    implementation = _impl,
    attrs = {
        "archives": attr.label_list(allow_files = True, mandatory = True),
        "_unpack": attr.label(default = Label("//:unpack"), executable = True, cfg = "exec"),
    },
    toolchains = [_TAR],
)
