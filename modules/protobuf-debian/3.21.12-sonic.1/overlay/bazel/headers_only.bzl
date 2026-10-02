"""Forward the declared Debian headers without unrelated library link inputs."""

load("@rules_cc//cc/common:cc_info.bzl", "CcInfo")

def _headers_only_impl(ctx):
    return [CcInfo(compilation_context = ctx.attr.library[CcInfo].compilation_context)]

headers_only = rule(
    implementation = _headers_only_impl,
    attrs = {"library": attr.label(mandatory = True, providers = [CcInfo])},
)
