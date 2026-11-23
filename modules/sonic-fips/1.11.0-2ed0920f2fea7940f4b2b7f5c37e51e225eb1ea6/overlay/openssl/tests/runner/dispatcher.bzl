"""Materialize executable OpenSSL suite dispatchers from unchanged templates."""

def _impl(ctx):
    output = ctx.actions.declare_file(ctx.label.name)
    ctx.actions.expand_template(
        template = ctx.file.template,
        output = output,
        substitutions = {},
        is_executable = True,
    )
    return [DefaultInfo(files = depset([output]))]

openssl_test_dispatcher = rule(
    implementation = _impl,
    attrs = {"template": attr.label(allow_single_file = True, mandatory = True)},
)
