"""Call deb_postfix from a generated repository with no archive-tool aliases."""

def _fixture_impl(ctx):
    ctx.file("BUILD.bazel", """load(%r, "deb_postfix")

package(default_visibility = ["//visibility:public"])

deb_postfix(name = "plain", srcs = [%r], outs = ["plain.tar.gz"])
deb_postfix(name = "merged", srcs = [%r], outs = ["merged.tar.gz"], mergedusr = True)
""" % (str(ctx.attr._postfix), str(ctx.attr._payload), str(ctx.attr._payload)))

archive_tool_fixture = repository_rule(
    implementation = _fixture_impl,
    attrs = {
        "_postfix": attr.label(default = Label("@rules_distroless//apt/private:deb_postfix.bzl")),
        "_payload": attr.label(default = Label(":payload")),
    },
)
