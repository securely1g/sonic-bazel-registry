"""Regression checks for native managed-GCC compile and link actions."""

load("@bazel_skylib//lib:unittest.bzl", "analysistest", "asserts")

def _link_contract_impl(ctx):
    env = analysistest.begin(ctx)
    actions = [a for a in analysistest.target_actions(env) if a.mnemonic == "CppLink"]
    asserts.equals(env, 1, len(actions))
    if len(actions) != 1:
        return analysistest.end(env)
    argv = actions[0].argv
    as_needed = [i for i in range(len(argv)) if argv[i] == "-Wl,--as-needed"]
    asserts.equals(env, 1, len(as_needed), "The shared toolchain enables --as-needed once by default")
    libraries = [i for i in range(len(argv)) if "libmanaged_dependency" in argv[i]]
    asserts.true(env, bool(libraries), "The consumer must link a real dependency")
    if as_needed and libraries:
        asserts.true(env, as_needed[0] < libraries[0], "--as-needed must precede dependency libraries")
    return analysistest.end(env)

link_contract_test = analysistest.make(_link_contract_impl)

def _compile_hardening_impl(ctx):
    env = analysistest.begin(ctx)
    actions = [a for a in analysistest.target_actions(env) if a.mnemonic == "CppCompile"]
    asserts.equals(env, 1, len(actions))
    for action in actions:
        argv = action.argv
        asserts.equals(env, 1, len([arg for arg in argv if arg == ctx.attr.expected]), "The native target must receive its supported CPU hardening option")
        asserts.equals(env, [], [arg for arg in argv if arg.startswith(ctx.attr.forbidden)], "Do not pass the other CPU's hardening option")
        for flag in ["-fstack-protector-strong", "-fstack-clash-protection", "-D_FORTIFY_SOURCE=2"]:
            asserts.true(env, flag in argv, "Preserve shared hardening flag: " + flag)
    return analysistest.end(env)

compile_hardening_test = analysistest.make(
    _compile_hardening_impl,
    attrs = {
        "expected": attr.string(mandatory = True),
        "forbidden": attr.string(mandatory = True),
    },
)
