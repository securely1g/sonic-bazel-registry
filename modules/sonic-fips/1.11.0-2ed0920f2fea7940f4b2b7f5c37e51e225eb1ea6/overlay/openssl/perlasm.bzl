"""Run OpenSSL perlasm with its target compiler capability checks.

The original perlasm scripts consult CC to decide which assembler instructions
are available. The compiler and its declared environment come from the target
C++ toolchain; Perl is an exec-configured managed tool.
"""

load("@rules_cc//cc:action_names.bzl", "ACTION_NAMES")
load("@rules_cc//cc:defs.bzl", "cc_common")
load("@rules_cc//cc:find_cc_toolchain.bzl", "find_cpp_toolchain", "use_cc_toolchain")

def _perlasm_impl(ctx):
    toolchain = find_cpp_toolchain(ctx)
    features = cc_common.configure_features(
        ctx = ctx,
        cc_toolchain = toolchain,
        requested_features = ctx.features,
        unsupported_features = ctx.disabled_features,
    )
    environment = dict(cc_common.get_environment_variables(
        feature_configuration = features,
        action_name = ACTION_NAMES.c_compile,
        variables = cc_common.empty_variables(),
    ))
    environment["CC"] = cc_common.get_tool_for_action(
        feature_configuration = features,
        action_name = ACTION_NAMES.c_compile,
    )
    args = ctx.actions.args()
    args.add(ctx.file.script)
    args.add(ctx.attr.flavor)
    args.add_all(ctx.attr.script_args)
    args.add(ctx.outputs.out)
    perl = ctx.attr._perl[DefaultInfo].files_to_run
    ctx.actions.run(
        executable = perl,
        arguments = [args],
        inputs = depset([ctx.file.script] + ctx.files.support, transitive = [toolchain.all_files]),
        tools = [perl],
        outputs = [ctx.outputs.out],
        env = environment,
        mnemonic = "OpenSSLPerlasm",
    )
    return [DefaultInfo(files = depset([ctx.outputs.out]))]

openssl_perlasm = rule(
    implementation = _perlasm_impl,
    attrs = {
        "script": attr.label(allow_single_file = True, mandatory = True),
        "support": attr.label_list(allow_files = True),
        "flavor": attr.string(mandatory = True),
        "script_args": attr.string_list(),
        "out": attr.output(mandatory = True),
        "_perl": attr.label(default = Label("@sonic_build_infra//tools/build_tools:perl"), executable = True, cfg = "exec"),
    },
    toolchains = use_cc_toolchain(),
    fragments = ["cpp"],
)
