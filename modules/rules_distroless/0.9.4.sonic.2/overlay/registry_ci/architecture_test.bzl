"""Exercise generated Debian architecture selection from a registry consumer."""

load("@bazel_skylib//lib:unittest.bzl", "analysistest", "asserts")

def _architecture_test_impl(ctx):
    env = analysistest.begin(ctx)
    target = analysistest.target_under_test(env)
    # The fixture has an empty set for each architecture. Reaching this point
    # proves that its generated select matched the requested CPU and OS.
    asserts.equals(env, [], target[DefaultInfo].files.to_list())
    return analysistest.end(env)

_amd64_test = analysistest.make(
    _architecture_test_impl,
    config_settings = {"//command_line_option:platforms": str(Label("//registry_ci:amd64"))},
)

_arm64_test = analysistest.make(
    _architecture_test_impl,
    config_settings = {"//command_line_option:platforms": str(Label("//registry_ci:arm64"))},
)

_armhf_test = analysistest.make(
    _architecture_test_impl,
    config_settings = {"//command_line_option:platforms": str(Label("//registry_ci:armhf"))},
)

def architecture_tests():
    _amd64_test(name = "architecture_amd64_test", target_under_test = "@registry_ci_architectures//:packages")
    _arm64_test(name = "architecture_arm64_test", target_under_test = "@registry_ci_architectures//:packages")
    _armhf_test(name = "architecture_armhf_test", target_under_test = "@registry_ci_architectures//:packages")
