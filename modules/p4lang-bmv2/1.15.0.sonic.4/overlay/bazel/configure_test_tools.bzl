"""Select the configure frontend's build tools for the execution machine."""

def _configure_test_tools_impl(ctx):
    return [DefaultInfo(files = ctx.attr.runtime[DefaultInfo].files)]

configure_test_tools = rule(
    implementation = _configure_test_tools_impl,
    attrs = {"runtime": attr.label(cfg = "exec", mandatory = True)},
)
