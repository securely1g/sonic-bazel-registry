"""Prepare Protobuf from the pinned Debian source archives."""

def _apply_patch(ctx, patch):
    # The original recipe disables backup creation on offset matches. The
    # shared gnu_patch helper does not expose this option, so keep that policy
    # while consuming its declared tool repository and private loader.
    root = ctx.path(ctx.attr.gnu_tools).dirname
    ctx.read(patch)
    ctx.read(root.get_child("manifest.json"))
    result = ctx.execute(
        [root.get_child("loader"), "--inhibit-cache", "--library-path", root.get_child("lib"), root.get_child("patch"), "--batch", "--forward", "--fuzz=0", "--no-backup-if-mismatch", "-p1", "--input=" + str(patch)],
        environment = {"PATH": "", "LC_ALL": "C", "LD_PRELOAD": "", "LD_LIBRARY_PATH": "", "LD_AUDIT": "", "GLIBC_TUNABLES": ""},
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
    # Debian's original patches need GNU patch's file-boundary and offset
    # handling. Never normalize or copy the distribution-owned patch files.
    for line in ctx.read("debian/patches/series").splitlines():
        fields = [part for part in line.split("#", 1)[0].replace("\t", " ").split(" ") if part]
        if not fields:
            continue
        if len(fields) != 1 or fields[0].startswith("/") or ".." in fields[0].split("/"):
            fail("Unsupported Debian patch entry: " + line)
        _apply_patch(ctx, ctx.path("debian/patches/" + fields[0]))
    _apply_patch(ctx, ctx.path(ctx.attr.integration_patch))

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
        "gnu_tools": attr.label(mandatory = True, allow_single_file = True),
        "upstream_url": attr.string(mandatory = True),
        "upstream_sha256": attr.string(mandatory = True),
        "debian_url": attr.string(mandatory = True),
        "debian_sha256": attr.string(mandatory = True),
        "integration_patch": attr.label(mandatory = True, allow_single_file = True),
        "overlays": attr.label_keyed_string_dict(mandatory = True, allow_files = True),
    },
)
