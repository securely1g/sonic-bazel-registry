load("@sonic_build_infra//binary:debug_symbols.bzl", "DebugSymbolsInfo")

"""Original install hook streams final ELF and target libc metadata to raw TAR."""

def _impl(ctx):
    out = ctx.actions.declare_file(ctx.label.name + ".tar")
    args = ctx.actions.args()
    args.add_all([ctx.file.elf, ctx.file.libc, ctx.file.config, ctx.file.copyright, out])
    docs = []
    for target, path in ctx.attr.docs.items():
        files = target[DefaultInfo].files.to_list()
        if len(files) != 1:
            fail("one installed documentation file required")
        docs.extend(files)
        args.add(path)
        args.add(files[0])
    tool = ctx.attr._tool[DefaultInfo].files_to_run
    ctx.actions.run(executable = tool, tools = [tool], arguments = [args], inputs = [ctx.file.elf, ctx.file.libc, ctx.file.config, ctx.file.copyright] + docs, outputs = [out], mnemonic = "NssInstallTar")
    return [DefaultInfo(files = depset([out])), ctx.attr.debug[DebugSymbolsInfo]]

nss_runtime_tar = rule(implementation = _impl, attrs = {"docs": attr.label_keyed_string_dict(allow_files = True), "debug": attr.label(providers = [DebugSymbolsInfo], mandatory = True), "elf": attr.label(allow_single_file = True, mandatory = True), "libc": attr.label(allow_single_file = True, mandatory = True), "config": attr.label(allow_single_file = True, mandatory = True), "copyright": attr.label(allow_single_file = True, mandatory = True), "_tool": attr.label(default = Label(":runtime_tar"), executable = True, cfg = "exec")})
