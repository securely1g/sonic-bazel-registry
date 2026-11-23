"""Run upstream Perl recipes against declared native test producers."""
def _rf(ctx, f):
    return f.short_path[3:] if f.short_path.startswith("../") else ctx.workspace_name + "/" + f.short_path

def _impl(ctx):
    links = {}
    prefix = "openssl-suite"
    for f in ctx.files.sources:
        path = f.short_path.split("/", 2)[2]
        links[prefix + "/source/" + path] = f
    manifest = ctx.actions.declare_file(ctx.label.name + ".json")
    entries = {}
    files = [manifest, ctx.file.driver, ctx.executable.perl, ctx.executable.python, ctx.file.kernel]
    targets = [ctx.attr.perl, ctx.attr.python, ctx.attr.kernel]
    for target, destination in ctx.attr.layout.items():
        selected = target[DefaultInfo].files.to_list()
        if len(selected) != 1:
            fail("Suite layout expects one file for " + str(target.label))
        entries[destination] = _rf(ctx, selected[0])
        files.extend(selected)
        targets.append(target)
    ctx.actions.write(manifest, json.encode(entries))
    executable = ctx.actions.declare_file(ctx.label.name)
    ctx.actions.write(executable, """#!/bin/sh
set -eu
runfiles=${RUNFILES_DIR:-${TEST_SRCDIR:-$0.runfiles}}
export RUNFILES_DIR=$runfiles
exec "$runfiles/%s" "$runfiles/%s" --runfiles "$runfiles" --source "$runfiles/%s/openssl-suite/source" --manifest "$runfiles/%s" --perl "$runfiles/%s" --kernel "$runfiles/%s" "$@"
""" % (_rf(ctx, ctx.executable.python), _rf(ctx, ctx.file.driver), ctx.workspace_name, _rf(ctx, manifest), _rf(ctx, ctx.executable.perl), _rf(ctx, ctx.file.kernel)), is_executable = True)
    runfiles = ctx.runfiles(files = files, symlinks = links)
    for target in targets:
        runfiles = runfiles.merge(target[DefaultInfo].default_runfiles).merge(target[DefaultInfo].data_runfiles)
    return [DefaultInfo(executable = executable, runfiles = runfiles)]

openssl_suite_test = rule(implementation = _impl, test = True, attrs = {
    "sources": attr.label_list(allow_files = True),
    "layout": attr.label_keyed_string_dict(allow_files = True),
    "driver": attr.label(default = "suite.py", allow_single_file = True),
    "perl": attr.label(default = "@sonic_build_infra//tools/build_tools:perl", executable = True, cfg = "exec"),
    "python": attr.label(default = "@sonic_build_infra//tools/build_tools:python3", executable = True, cfg = "exec"),
    "kernel": attr.label(default = "@sonic_build_infra//tools/build_tools:kernel_runtime", allow_single_file = True, cfg = "exec"),
})
