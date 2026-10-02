"""Package upstream-generated files with stable paths and output groups."""

load(":protobuf.bzl", "proto_gen")

def _join(parts):
    return "/".join([part for part in parts if part])

def _directory(value, name):
    if value.startswith("/") or ".." in value.split("/"):
        fail("{} must be a relative path without '..': {}".format(name, value))
    return value.strip("/")

def _outputs(srcs, strip_import_prefix, output_prefix, suffix):
    prefix = _directory(strip_import_prefix, "strip_import_prefix")
    output = _directory(output_prefix, "output_prefix")
    result = []
    package = native.package_name()
    caller = native.package_relative_label(":__proto_context__")
    for src in srcs:
        label = native.package_relative_label(src)
        if label.workspace_name != caller.workspace_name or label.package != package:
            fail("proto sources must be in the current repository and package: {}".format(src))
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

def _generated_files_impl(ctx):
    groups = {}
    for group in ["sources", "headers", "python", "pyi"]:
        inputs = getattr(ctx.files, group + "_inputs")
        outputs = getattr(ctx.outputs, group)
        for source, output in zip(inputs, outputs):
            ctx.actions.symlink(output = output, target_file = source)
        groups[group] = depset(outputs + getattr(ctx.files, group + "_passthrough"))
    return [DefaultInfo(files = depset(transitive = groups.values())), OutputGroupInfo(**groups)]

_generated_files = rule(
    implementation = _generated_files_impl,
    attrs = dict(
        [(group + "_inputs", attr.label_list(allow_files = True)) for group in ["sources", "headers", "python", "pyi"]] +
        [(group, attr.output_list()) for group in ["sources", "headers", "python", "pyi"]] +
        [(group + "_passthrough", attr.label_list(allow_files = True)) for group in ["sources", "headers", "python", "pyi"]],
    ),
)

def _sources(name, srcs, strip_import_prefix, output_prefix, suffixes, **kwargs):
    upstream_outputs = {group: _outputs(srcs, "", "", suffix) for group, suffix in suffixes.items()}
    proto_gen(
        name = name + "_upstream",
        srcs = srcs,
        deps = [Label("//:cc_wkt_protos_genproto")],
        includes = [strip_import_prefix],
        protoc = Label("//:protoc"),
        gen_cc = "sources" in suffixes,
        gen_py = "python" in suffixes,
        gen_pyi = "pyi" in suffixes,
        outs = [path for paths in upstream_outputs.values() for path in paths],
        visibility = ["//visibility:private"],
    )
    attributes = {}
    for group, suffix in suffixes.items():
        outputs = _outputs(srcs, strip_import_prefix, output_prefix, suffix)
        pairs = zip(upstream_outputs[group], outputs)
        attributes[group + "_inputs"] = [source for source, target in pairs if source != target]
        attributes[group] = [target for source, target in pairs if source != target]
        attributes[group + "_passthrough"] = [source for source, target in pairs if source == target]
    _generated_files(name = name, **dict(attributes, **kwargs))

def cpp_proto_sources(name, srcs, strip_import_prefix = "", output_prefix = "", **kwargs):
    """Generate addressable .pb.cc/.pb.h files with upstream proto_gen."""
    _sources(name, srcs, strip_import_prefix, output_prefix, {"sources": ".pb.cc", "headers": ".pb.h"}, **kwargs)

def python_proto_sources(name, srcs, strip_import_prefix = "", output_prefix = "", **kwargs):
    """Generate addressable _pb2.py/_pb2.pyi files with upstream proto_gen."""
    _sources(name, srcs, strip_import_prefix, output_prefix, {"python": "_pb2.py", "pyi": "_pb2.pyi"}, **kwargs)
