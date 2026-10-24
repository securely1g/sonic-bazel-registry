"""Prepare the exact SONiC PI 0.1.3-2 source package for its upstream Make build."""
def _impl(ctx):
    ctx.download_and_extract(url = ctx.attr.upstream_url, sha256 = ctx.attr.upstream_sha256, type = "tar.gz")
    ctx.download_and_extract(url = ctx.attr.debian_url, sha256 = ctx.attr.debian_sha256, type = "tar.xz")
    # This source package has no Debian patches. Do not silently ignore a series.
    if ctx.path("debian/patches/series").exists:
        fail("Unexpected Debian patch series in pinned PI source")
    # Mirror the source adjustment in the exact Debian rules used by SONiC.
    proto = "proto/p4runtime/proto/p4/config/v1/p4info.proto"
    ctx.file(proto, ctx.read(proto).replace("optional ", ""), executable = False)
    # This build uses upstream Autotools. Remove only the pinned source's Bazel
    # package boundaries so its complete source tree is visible to foreign_cc.
    for path in ['BUILD', 'bazel/BUILD', 'frontends_extra/cpp/BUILD', 'lib/BUILD', 'proto/BUILD', 'proto/frontend/BUILD', 'proto/p4info/BUILD', 'proto/p4runtime/bazel/example/BUILD.bazel', 'proto/p4runtime/proto/BUILD.bazel', 'proto/server/BUILD', 'proto/tests/BUILD', 'proto/third_party/BUILD', 'tests/BUILD', 'third_party/BUILD', 'third_party/cJSON/BUILD', 'third_party/googletest/BUILD.bazel', 'third_party/googletest/googlemock/test/BUILD.bazel', 'third_party/googletest/googletest/test/BUILD.bazel']:
        if not ctx.path(path).exists:
            fail("Missing pinned upstream Bazel metadata: " + path)
        ctx.delete(path)
    ctx.symlink(ctx.attr.build_file, "BUILD.bazel")
    ctx.symlink(ctx.attr.configure_file, "bazel/configure.sh")
    ctx.symlink(ctx.attr.runtime_file, "bazel/runtime.bzl")

pi_source = repository_rule(implementation = _impl, attrs = {
    "upstream_url": attr.string(mandatory = True), "upstream_sha256": attr.string(mandatory = True),
    "debian_url": attr.string(mandatory = True), "debian_sha256": attr.string(mandatory = True),
    "build_file": attr.label(mandatory = True, allow_single_file = True),
    "configure_file": attr.label(mandatory = True, allow_single_file = True),
    "runtime_file": attr.label(mandatory = True, allow_single_file = True),
})
