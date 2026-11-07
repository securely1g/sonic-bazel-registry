"""Execution toolchain selection for source-built gawk and its runtime."""

def _toolchain_impl(ctx):
    default = ctx.attr.binary[DefaultInfo]
    return [platform_common.ToolchainInfo(gawk = default.files_to_run, default = default)]

gawk_toolchain = rule(
    implementation = _toolchain_impl,
    attrs = {"binary": attr.label(mandatory = True, executable = True, cfg = "exec")},
)

def _resolved_impl(ctx):
    toolchain = ctx.toolchains["//:toolchain_type"]
    tool = toolchain.gawk.executable
    executable = ctx.actions.declare_file(ctx.label.name)
    ctx.actions.symlink(output = executable, target_file = tool, is_executable = True)
    return [DefaultInfo(executable = executable, runfiles = ctx.runfiles(files = [tool]).merge(toolchain.default.default_runfiles))]

resolved_gawk = rule(implementation = _resolved_impl, executable = True, toolchains = ["//:toolchain_type"])
