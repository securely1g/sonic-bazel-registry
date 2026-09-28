"""Expose a shared library's public dependency headers without relinking it."""

load("@rules_cc//cc:defs.bzl", "CcInfo")

def _headers_only_impl(ctx):
    return [CcInfo(compilation_context = ctx.attr.dep[CcInfo].compilation_context)]

headers_only = rule(
    implementation = _headers_only_impl,
    attrs = {"dep": attr.label(mandatory = True, providers = [CcInfo])},
)
