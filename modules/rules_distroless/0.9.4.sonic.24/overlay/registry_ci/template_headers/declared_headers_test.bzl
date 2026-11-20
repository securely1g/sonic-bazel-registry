"""Require the actual imported Boost template files, even on hosts with Boost."""

load("@bazel_skylib//lib:unittest.bzl", "analysistest", "asserts")
load("@rules_cc//cc/common:cc_info.bzl", "CcInfo")
load("//apt/private:headers.bzl", "is_include_fragment")

def _impl(ctx):
    env = analysistest.begin(ctx)
    target = analysistest.target_under_test(env)
    headers = [file.short_path for file in target[CcInfo].compilation_context.headers.to_list()]
    for path in [
        "boost/xpressive/detail/utility/chset/basic_chset.ipp",
        "boost/spirit/home/classic/utility/impl/chset/basic_chset.ipp",
    ]:
        asserts.true(env, any([header.endswith("/usr/include/" + path) for header in headers]), "Missing declared template header: " + path)
    for path in ["usr/include/lib/template.tcc", "usr/include/lib/private.hxx", "usr/include/lib/code.ipp"]:
        asserts.true(env, is_include_fragment(path), path)
    for path in ["usr/share/doc/template.ipp", "usr/include/lib/template.ipp.in", "usr/include/lib/object.o"]:
        asserts.false(env, is_include_fragment(path), path)
    return analysistest.end(env)

declared_headers_test = analysistest.make(_impl)
