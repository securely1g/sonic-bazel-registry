"""Generate metadata from the fixed SAI source and DASH API headers."""

_METADATA_OUTPUTS = [
    "saimetadata.c",
    "saimetadata.h",
    "saimetadatatest.c",
    "saiswig.i",
    "saiattrversion.h",
    "saimetadatasize.h",
]

def _file_map(files, group):
    result = {}
    for file in files:
        if file.basename in result:
            fail("duplicate SAI metadata input in %s: %s" % (group, file.basename))
        result[file.basename] = file.path
    return result

def _dash_metadata_impl(ctx):
    groups = {
        ".": ctx.files.meta,
        "../inc/": ctx.files.inc,
        "../experimental/": ctx.files.experimental,
        "../custom/": ctx.files.custom,
    }
    paths = {group: _file_map(files, group) for group, files in groups.items()}
    manifest = ctx.actions.declare_file(ctx.label.name + ".inputs.json")
    ctx.actions.write(manifest, json.encode(paths))

    args = ctx.actions.args()
    args.add("--manifest", manifest)
    args.add("--parser", ctx.file.parser)
    tools = [ctx.attr._doxygen, ctx.attr._perl, ctx.attr._aspell]
    for name, tool in zip(["doxygen", "perl", "aspell"], tools):
        args.add("--" + name, tool[DefaultInfo].files_to_run.executable)
    args.add_all(ctx.outputs.outputs, before_each = "--output")
    ctx.actions.run(
        executable = ctx.attr._driver[DefaultInfo].files_to_run,
        tools = [tool[DefaultInfo].files_to_run for tool in tools],
        inputs = depset(
            direct = [manifest, ctx.file.parser],
            transitive = [depset(files) for files in groups.values()],
        ),
        outputs = ctx.outputs.outputs,
        arguments = [args],
        mnemonic = "GenerateDashSaiMetadata",
    )
    return DefaultInfo(files = depset(ctx.outputs.outputs))

_dash_metadata = rule(
    implementation = _dash_metadata_impl,
    attrs = {
        "inc": attr.label_list(allow_files = [".h"], mandatory = True),
        "experimental": attr.label_list(allow_files = [".h"], mandatory = True),
        "custom": attr.label_list(allow_files = [".h"]),
        "meta": attr.label_list(allow_files = True, mandatory = True),
        "parser": attr.label(allow_single_file = [".pl"], mandatory = True),
        "outputs": attr.output_list(mandatory = True),
        "_driver": attr.label(
            default = Label("//bazel:generate_metadata"),
            executable = True,
            cfg = "exec",
        ),
        "_aspell": attr.label(
            default = Label("@sonic_build_infra//tools/build_tools:aspell"),
            executable = True,
            cfg = "exec",
        ),
        "_doxygen": attr.label(
            default = Label("@sonic_build_infra//tools/build_tools:doxygen"),
            executable = True,
            cfg = "exec",
        ),
        "_perl": attr.label(
            default = Label("@sonic_build_infra//tools/build_tools:perl"),
            executable = True,
            cfg = "exec",
        ),
    },
)

def dash_metadata(name, **kwargs):
    _dash_metadata(
        name = name,
        outputs = [name + "/" + filename for filename in _METADATA_OUTPUTS],
        **kwargs
    )
