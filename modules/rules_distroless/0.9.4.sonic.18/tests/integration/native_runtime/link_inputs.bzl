"""Expose the declared link inputs to a compiler invocation without inferred RPATHs."""

load("@bazel_skylib//lib:shell.bzl", "shell")
load("@rules_cc//cc:defs.bzl", "CcInfo")

def _impl(ctx):
    files = []
    flags = []
    for item in ctx.attr.dep[CcInfo].linking_context.linker_inputs.to_list():
        files.extend(item.additional_inputs)
        flags.extend(item.user_link_flags)
        for library in item.libraries:
            # A real link consumes the interface instead of the runtime DSO
            # when one exists. Runtime symlinks used by -rpath-link must also
            # be explicitly declared, rather than injected by this fixture.
            file = library.interface_library or library.dynamic_library or library.static_library
            if file:
                files.append(file)
    return [
        DefaultInfo(files = depset(files)),
        platform_common.TemplateVariableInfo({"APT_NATIVE_FLAGS": " ".join([shell.quote(flag) for flag in flags])}),
    ]

link_inputs = rule(implementation = _impl, attrs = {"dep": attr.label(providers = [CcInfo])})
