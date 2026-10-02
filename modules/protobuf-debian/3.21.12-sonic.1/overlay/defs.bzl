"""Declared C++ and Python outputs from the matching shared Debian protoc."""

def _join(parts):
    return "/".join([part for part in parts if part])

def _directory(value, name):
    if value.startswith("/") or ".." in value.split("/"):
        fail("{} must be a relative path without '..': {}".format(name, value))
    return value.strip("/")

def _proto_sources_impl(ctx):
    package_root = _join([ctx.label.workspace_root, ctx.label.package])
    proto_root = _join([package_root, ctx.attr.strip_import_prefix])
    output_root = _join([ctx.bin_dir.path, package_root, ctx.attr.output_prefix])
    args = ctx.actions.args()
    args.add("--proto_path=" + (proto_root or "."))
    if ctx.outputs.sources:
        args.add("--cpp_out=" + output_root)
    if ctx.outputs.python:
        args.add("--python_out=" + output_root)
        args.add("--pyi_out=" + output_root)
    args.add("--experimental_allow_proto3_optional")
    args.add_all(ctx.files.srcs)
    outputs = ctx.outputs.sources + ctx.outputs.headers + ctx.outputs.python + ctx.outputs.pyi
    ctx.actions.run(
        executable = ctx.executable._protoc,
        arguments = [args],
        inputs = ctx.files.srcs,
        outputs = outputs,
        tools = [ctx.attr._protoc[DefaultInfo].files_to_run],
        mnemonic = "DebianProtoSources",
        progress_message = "Generating protobuf sources for %{label}",
    )
    return [
        DefaultInfo(files = depset(outputs)),
        OutputGroupInfo(
            sources = depset(ctx.outputs.sources),
            headers = depset(ctx.outputs.headers),
            python = depset(ctx.outputs.python),
            pyi = depset(ctx.outputs.pyi),
        ),
    ]

_proto_sources = rule(
    implementation = _proto_sources_impl,
    attrs = {
        "srcs": attr.label_list(allow_files = [".proto"], mandatory = True),
        "strip_import_prefix": attr.string(),
        "output_prefix": attr.string(),
        "sources": attr.output_list(),
        "headers": attr.output_list(),
        "python": attr.output_list(),
        "pyi": attr.output_list(),
        "_protoc": attr.label(default = Label("@sonic_build_infra//proto:protoc"), executable = True, cfg = "exec"),
    },
)

def _outputs(srcs, strip_import_prefix, output_prefix, suffix):
    prefix = _directory(strip_import_prefix, "strip_import_prefix")
    output = _directory(output_prefix, "output_prefix")
    result = []
    package = native.package_name()
    caller = native.package_relative_label(":__proto_context__")
    for src in srcs:
        label = native.package_relative_label(src)
        if label.workspace_name != caller.workspace_name or (package and label.package != package and not label.package.startswith(package + "/")):
            fail("proto sources must be in the current repository and package subtree: {}".format(src))
        path = _join([label.package, label.name])
        if package:
            path = path[len(package) + 1:]
        if prefix:
            if not path.startswith(prefix + "/"):
                fail("{} is outside proto import root {}".format(src, prefix))
            path = path[len(prefix) + 1:]
        if not path.endswith(".proto"):
            fail("Expected a .proto input: {}".format(src))
        result.append(_join([output, path[:-6] + suffix]))
    return result

def cpp_proto_sources(name, srcs, strip_import_prefix = "", output_prefix = "", **kwargs):
    """Generate individually addressable .pb.cc/.pb.h outputs and output groups."""
    _proto_sources(
        name = name,
        srcs = srcs,
        strip_import_prefix = strip_import_prefix,
        output_prefix = output_prefix,
        sources = _outputs(srcs, strip_import_prefix, output_prefix, ".pb.cc"),
        headers = _outputs(srcs, strip_import_prefix, output_prefix, ".pb.h"),
        **kwargs
    )

def python_proto_sources(name, srcs, strip_import_prefix = "", output_prefix = "", **kwargs):
    """Generate individually addressable _pb2.py/_pb2.pyi outputs and output groups."""
    _proto_sources(
        name = name,
        srcs = srcs,
        strip_import_prefix = strip_import_prefix,
        output_prefix = output_prefix,
        python = _outputs(srcs, strip_import_prefix, output_prefix, "_pb2.py"),
        pyi = _outputs(srcs, strip_import_prefix, output_prefix, "_pb2.pyi"),
        **kwargs
    )
