"""Headerless runtime dependencies must not add nonexistent include roots."""

load("@bazel_skylib//lib:unittest.bzl", "analysistest", "asserts")
load("@rules_cc//cc/common:cc_info.bzl", "CcInfo")

def _impl(ctx):
    env = analysistest.begin(ctx)
    info = analysistest.target_under_test(env)[CcInfo]
    headers = info.compilation_context.headers.to_list()
    includes = info.compilation_context.system_includes.to_list()
    asserts.equals(env, ctx.attr.expected_headers, len(headers))
    asserts.equals(env, ctx.attr.expected_headers, len(includes))
    for header in headers:
        asserts.true(env, header.path.endswith("/fixture.h"))
    for include in includes:
        asserts.true(env, include.endswith("/usr/include"))
    flags = [flag for item in info.linking_context.linker_inputs.to_list() for flag in item.user_link_flags]
    asserts.equals(env, ctx.attr.expected_flags, flags)
    return analysistest.end(env)

context_test = analysistest.make(
    _impl,
    attrs = {
        "expected_headers": attr.int(),
        "expected_flags": attr.string_list(),
    },
)
