"""Check that only an empty dynamic pkg-config input loses its static carrier."""

load("@bazel_skylib//lib:unittest.bzl", "asserts", "unittest")
load("@rules_cc//cc/common:cc_info.bzl", "CcInfo")

def _has_anchor(target):
    for item in target[CcInfo].linking_context.linker_inputs.to_list():
        for library in item.libraries:
            if library.static_library and library.static_library.basename == "linkopts.a":
                return True
    return False

def _impl(ctx):
    env = unittest.begin(ctx)
    asserts.false(env, _has_anchor(ctx.attr.header_only), str(ctx.attr.header_only.label))
    for target in ctx.attr.anchored:
        asserts.true(env, _has_anchor(target), str(target.label))
    return unittest.end(env)

link_ownership_test = unittest.make(_impl, attrs = {
    "header_only": attr.label(providers = [CcInfo], mandatory = True),
    "anchored": attr.label_list(providers = [CcInfo], mandatory = True),
})
