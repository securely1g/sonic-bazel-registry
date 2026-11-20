load("@rules_cc//cc:defs.bzl", "CcInfo")
load("@rules_cc//cc/common:cc_common.bzl", "cc_common")

def _headers_impl(ctx):
    root = ctx.files.hdrs[0].dirname
    directories = [root] + [root + "/" + x for x in ctx.attr.extra_roots]
    field = "includes" if ctx.attr.kind == "ordinary" else ctx.attr.kind + "_includes"
    return [CcInfo(compilation_context = cc_common.create_compilation_context(
        headers = depset(ctx.files.hdrs),
        **{field: depset(directories)}
    ))]

classified_headers = rule(
    implementation = _headers_impl,
    attrs = {
        "hdrs": attr.label_list(allow_files = True),
        "kind": attr.string(values = ["ordinary", "system", "quote"]),
        "extra_roots": attr.string_list(),
    },
)

def _receipt_test_impl(ctx):
    receipts = [f for dep in ctx.attr.deps for f in dep[DefaultInfo].files.to_list() if f.basename == "receipt.txt"]
    if len(receipts) != len(ctx.attr.deps):
        fail("Each builder must publish its executed compiler-check receipt")
    script = ctx.actions.declare_file(ctx.label.name + ".sh")
    lines = ["#!/bin/sh", "set -eu"]
    for receipt in receipts:
        lines.append('test -s "$TEST_SRCDIR/$TEST_WORKSPACE/' + receipt.short_path + '"')
    ctx.actions.write(script, "\n".join(lines) + "\n", is_executable = True)
    return [DefaultInfo(executable = script, runfiles = ctx.runfiles(files = receipts))]

receipt_test = rule(implementation = _receipt_test_impl, test = True, attrs = {"deps": attr.label_list()})
