"""Expose the original installed libtac/ namespace without copying source headers."""

def _impl(ctx):
    outputs = []
    originals = []
    for target, name in ctx.attr.headers.items():
        source = target[DefaultInfo].files.to_list()
        if len(source) != 1:
            fail("one original header required")
        output = ctx.actions.declare_file(ctx.label.name + "/libtac/" + name)
        ctx.actions.symlink(output = output, target_file = source[0])
        originals.extend(source)
        outputs.append(output)
    return [DefaultInfo(files = depset(outputs + originals))]

installed_header_aliases = rule(implementation = _impl, attrs = {"headers": attr.label_keyed_string_dict(allow_files = [".h"])})
