"""Keep the original NSS installation hook separate from Debian stripping."""

load("@rules_cc//cc:action_names.bzl", "ACTION_NAMES")
load("@rules_cc//cc:defs.bzl", "cc_common")
load("@rules_cc//cc:find_cc_toolchain.bzl", "find_cc_toolchain", "use_cc_toolchain")

def _impl(ctx):
    # Same declared CC tool selection used by sonic_deb, with the target ABI
    # retained for cross toolchains. The executable runs on the exec platform.
    toolchain = find_cc_toolchain(ctx)
    features = cc_common.configure_features(
        ctx = ctx,
        cc_toolchain = toolchain,
        requested_features = ctx.features,
        unsupported_features = ctx.disabled_features,
    )
    strip = cc_common.get_tool_for_action(feature_configuration = features, action_name = ACTION_NAMES.strip)
    ctx.actions.run(
        executable = strip,
        arguments = ["--keep-symbol=_nss_tacplus_getpwnam_r", "-o", ctx.outputs.out.path, ctx.file.src.path],
        inputs = depset([ctx.file.src], transitive = [toolchain.all_files]),
        outputs = [ctx.outputs.out],
        mnemonic = "NssInstallStrip",
        progress_message = "Preserving the original NSS entry symbol in the installation copy",
    )
    return [DefaultInfo(files = depset([ctx.outputs.out]))]

nss_install_strip = rule(
    implementation = _impl,
    attrs = {
        "src": attr.label(allow_single_file = True, mandatory = True),
        "out": attr.output(mandatory = True),
    },
    fragments = ["cpp"],
    toolchains = use_cc_toolchain(),
)
