"""Regression checks for the managed GCC link action consumed externally."""

load("@bazel_skylib//lib:unittest.bzl", "analysistest", "asserts")

def _link_contract_impl(ctx):
    env = analysistest.begin(ctx)
    actions = [a for a in analysistest.target_actions(env) if a.mnemonic == "CppLink"]
    asserts.equals(env, 1, len(actions))
    if len(actions) != 1:
        return analysistest.end(env)
    argv = actions[0].argv
    as_needed = [i for i in range(len(argv)) if argv[i] == "-Wl,--as-needed"]
    asserts.equals(env, ctx.attr.as_needed_count, len(as_needed), "--as-needed must be selected exactly once when enabled")
    host_rpath_links = [arg for arg in argv if arg.startswith("-Wl,-rpath-link=/lib/")]
    asserts.equals(env, [], host_rpath_links, "Link-time dependencies must come from managed inputs")
    libraries = [i for i in range(len(argv)) if "libmanaged_dependency" in argv[i]]
    asserts.true(env, bool(libraries), "The consumer must link a real dependency")
    if as_needed and libraries:
        asserts.true(env, as_needed[0] < libraries[0], "--as-needed must precede dependency libraries")
    return analysistest.end(env)

link_contract_test = analysistest.make(
    _link_contract_impl,
    attrs = {"as_needed_count": attr.int(mandatory = True)},
)
