"""Test-only extraction of the installed shell for a deployment runtime check."""
def _impl(ctx):
    output = ctx.actions.declare_file(ctx.label.name + ".elf")
    ctx.actions.run(executable = ctx.executable._tool, arguments = [ctx.file.payload.path, output.path],
                    inputs = [ctx.file.payload], outputs = [output], mnemonic = "InstalledBashTestBinary")
    return [DefaultInfo(files = depset([output]))]

installed_bash_test_binary = rule(
    implementation = _impl,
    attrs = {
        "payload": attr.label(allow_single_file = True, mandatory = True),
        "_tool": attr.label(default = Label(":test_extract_tool"), executable = True, cfg = "exec"),
    },
)
