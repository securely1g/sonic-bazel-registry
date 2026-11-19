"""Inspect actual imported CcInfo on both target platforms without host probing."""

load("@bazel_skylib//lib:unittest.bzl", "analysistest", "asserts")
load("@rules_cc//cc/common:cc_info.bzl", "CcInfo")

def _impl(ctx):
    env = analysistest.begin(ctx)
    cc = analysistest.target_under_test(env)[CcInfo].compilation_context
    roots = cc.system_includes.to_list()
    multiarch = [root for root in roots if "/usr/include/" in root and "-linux-" in root.split("/usr/include/", 1)[1]]
    asserts.true(env, len(multiarch) > 0, "The target's multiarch search path must be exported")
    for root in multiarch:
        asserts.true(env, root.endswith("/usr/include/" + ctx.attr.triplet), "Wrong-architecture include root: " + root)
    headers = [header.path for header in cc.headers.to_list()]

    # Header selection must not drop the actual declared symlink outputs.
    asserts.true(env, any([path.endswith("/usr/include/" + ctx.attr.triplet + "/asm/unistd.h") for path in headers]))
    return analysistest.end(env)

linux_headers_provider_test = analysistest.make(
    _impl,
    attrs = {"triplet": attr.string(mandatory = True)},
)
