"""Generate OpenSSL compiler metadata from the selected native toolchain."""
load("@rules_cc//cc:action_names.bzl", "ACTION_NAMES")
load("@rules_cc//cc:defs.bzl", "cc_common")
load("@rules_cc//cc:find_cc_toolchain.bzl", "find_cpp_toolchain", "use_cc_toolchain")

def _impl(ctx):
    toolchain = find_cpp_toolchain(ctx)
    features = cc_common.configure_features(ctx = ctx, cc_toolchain = toolchain, requested_features = ctx.features, unsupported_features = ctx.disabled_features)
    compiler = cc_common.get_tool_for_action(feature_configuration = features, action_name = ACTION_NAMES.c_compile).rsplit("/", 1)[-1]
    flags = [compiler] + ctx.attr.copts + ["-D" + define for define in ctx.attr.defines]
    perl = ctx.attr._perl[DefaultInfo].files_to_run
    ctx.actions.run_shell(
        command = '"$1" "$2" "$3" "$4" >"$5"',
        arguments = [ctx.executable._perl.path, ctx.file.script.path, " ".join(flags), ctx.attr.platform, ctx.outputs.out.path],
        inputs = [ctx.file.script],
        tools = [perl],
        outputs = [ctx.outputs.out],
        env = {"SOURCE_DATE_EPOCH": ctx.attr.source_date_epoch},
        mnemonic = "OpenSSLBuildInfo",
    )
    return [DefaultInfo(files = depset([ctx.outputs.out]))]

openssl_buildinfo = rule(implementation = _impl, attrs = {
    "script": attr.label(default = Label("@openssl_src//:util/mkbuildinf.pl"), allow_single_file = True),
    "copts": attr.string_list(),
    "defines": attr.string_list(),
    "platform": attr.string(mandatory = True),
    "source_date_epoch": attr.string(mandatory = True),
    "out": attr.output(mandatory = True),
    "_perl": attr.label(default = Label("@sonic_build_infra//tools/build_tools:perl"), executable = True, cfg = "exec"),
}, toolchains = use_cc_toolchain(), fragments = ["cpp"])
