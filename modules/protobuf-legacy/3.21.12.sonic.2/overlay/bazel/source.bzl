"""Prepare Protobuf from the pinned Debian source archives."""

def _apply_patch(ctx, patch_tool, patch, strip):
    result = ctx.execute(
        [patch_tool, "--batch", "--forward", "--fuzz=0", "--no-backup-if-mismatch", "-p" + str(strip), "-i", patch],
        environment = {"LC_ALL": "C"},
        quiet = True,
    )
    if result.return_code:
        fail("Cannot apply {}:\n{}{}".format(patch, result.stdout, result.stderr))

def _protobuf_source_impl(ctx):
    ctx.download_and_extract(
        url = ctx.attr.upstream_url,
        sha256 = ctx.attr.upstream_sha256,
        stripPrefix = "protobuf-3.21.12",
    )
    ctx.download_and_extract(url = ctx.attr.debian_url, sha256 = ctx.attr.debian_sha256)
    patch_tool = ctx.which("patch")
    if not patch_tool:
        fail("Preparing Debian's source series requires GNU patch")
    version = ctx.execute([patch_tool, "--version"], quiet = True)
    if version.return_code or not version.stdout.startswith("GNU patch "):
        fail("Preparing Debian's source series requires GNU patch")

    # Debian's original patches need GNU patch's file-boundary and offset
    # handling. Never normalize or copy the distribution-owned patch files.
    for line in ctx.read("debian/patches/series").splitlines():
        fields = [part for part in line.split("#", 1)[0].replace("\t", " ").split(" ") if part]
        if not fields:
            continue
        if len(fields) != 1 or fields[0].startswith("/") or ".." in fields[0].split("/"):
            fail("Unsupported Debian patch entry: " + line)
        _apply_patch(ctx, patch_tool, ctx.path("debian/patches/" + fields[0]), 1)
    _apply_patch(ctx, patch_tool, ctx.path(ctx.attr.integration_patch), 1)

    for source, destination in ctx.attr.overlays.items():
        ctx.symlink(source, destination)
    ctx.file("debian/BUILD.bazel", """exports_files(["control", "changelog", "copyright", "patches/series"])
filegroup(
    name = "source_files",
    srcs = glob(["**"], exclude = ["BUILD.bazel"]),
    visibility = ["//visibility:public"],
)
""", executable = False)
    ctx.file("BUILD.bazel", ctx.read("BUILD.bazel") + """
filegroup(
    name = "source_preparation_inputs",
    srcs = glob(["src/**", "python/**"]) + ["//debian:source_files"],
    visibility = ["//visibility:public"],
)
""", executable = False)

protobuf_source = repository_rule(
    implementation = _protobuf_source_impl,
    attrs = {
        "upstream_url": attr.string(mandatory = True),
        "upstream_sha256": attr.string(mandatory = True),
        "debian_url": attr.string(mandatory = True),
        "debian_sha256": attr.string(mandatory = True),
        "integration_patch": attr.label(mandatory = True, allow_single_file = True),
        "overlays": attr.label_keyed_string_dict(mandatory = True, allow_files = True),
    },
)
