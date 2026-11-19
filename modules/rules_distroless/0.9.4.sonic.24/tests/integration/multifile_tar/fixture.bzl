"""A real tar executable whose public default files include a companion tree."""

def _tool_impl(ctx):
    launcher = ctx.actions.declare_file(ctx.label.name)
    runtime = ctx.actions.declare_directory(ctx.label.name + ".runtime")
    ctx.actions.run(
        executable = ctx.executable._generator,
        arguments = ["tool", launcher.path, runtime.path, ctx.executable.tar.path],
        outputs = [launcher, runtime],
    )
    return [DefaultInfo(
        executable = launcher,
        files = depset([launcher, runtime] + ctx.files.tar),
    )]

multifile_tool = rule(
    implementation = _tool_impl,
    executable = True,
    attrs = {
        "tar": attr.label(executable = True, allow_single_file = True, cfg = "exec", mandatory = True),
        "_generator": attr.label(default = Label(":fixture_generator"), executable = True, cfg = "exec"),
    },
)

def _payload_impl(ctx):
    output = ctx.actions.declare_file(ctx.label.name + ".tar")
    ctx.actions.run(
        executable = ctx.executable._generator,
        arguments = ["payload", output.path],
        outputs = [output],
    )
    return [DefaultInfo(files = depset([output]))]

payload = rule(
    implementation = _payload_impl,
    attrs = {"_generator": attr.label(default = Label(":fixture_generator"), executable = True, cfg = "exec")},
)

def _repository_impl(ctx):
    ctx.file("BUILD.bazel", """load(%r, "deb_export")
package(default_visibility = ["//visibility:public"])
deb_export(
    name = "export",
    srcs = [%r],
    outs = ["usr/share/closure/payload.txt", "usr/bin/closure-probe"],
    foreign_symlinks = {},
    symlink_outs = [],
)
""" % (str(ctx.attr._deb_export), str(ctx.attr._payload)))

unpack_fixture = repository_rule(
    implementation = _repository_impl,
    attrs = {
        "_deb_export": attr.label(default = Label("@rules_distroless//apt/private:deb_export.bzl")),
        "_payload": attr.label(default = Label(":payload")),
    },
)
