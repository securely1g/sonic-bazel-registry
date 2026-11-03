"""Select the compiled objects belonging to one upstream static archive."""

load("@rules_cc//cc/common:cc_common.bzl", "cc_common")
load("@rules_cc//cc/common:cc_info.bzl", "CcInfo")

def _archive_inputs_impl(ctx):
    # cc_static_library normally includes transitive libraries. Automake's
    # libnl-route-3.a contains route and parser objects, but not libnl-3 objects.
    # Keep the existing libraries unchanged and select their own linker inputs.
    owners = {dep.label: True for dep in ctx.attr.deps}
    inputs = {}
    for dep in ctx.attr.deps:
        for linker_input in dep[CcInfo].linking_context.linker_inputs.to_list():
            if linker_input.owner in owners:
                inputs[linker_input.owner] = linker_input
    missing = [owner for owner in owners if owner not in inputs]
    if missing:
        fail("Missing direct archive objects for %s" % missing)
    compilation = cc_common.merge_cc_infos(cc_infos = [dep[CcInfo] for dep in ctx.attr.deps])
    return [CcInfo(
        compilation_context = compilation.compilation_context,
        linking_context = cc_common.create_linking_context(linker_inputs = depset(inputs.values())),
    )]

archive_inputs = rule(
    implementation = _archive_inputs_impl,
    attrs = {"deps": attr.label_list(providers = [CcInfo], mandatory = True)},
)
