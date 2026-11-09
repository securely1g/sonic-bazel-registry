"""Prepare socat's Debian source package, including SONiC's readline change."""

def _socat_source_impl(ctx):
    ctx.download_and_extract(
        url = ctx.attr.upstream_urls,
        sha256 = ctx.attr.upstream_sha256,
        stripPrefix = "socat-1.8.0.2",
        type = "tar.bz2",
    )
    ctx.download_and_extract(
        url = ctx.attr.debian_urls,
        sha256 = ctx.attr.debian_sha256,
        type = "tar.xz",
    )

    # Debian owns both the patches and their application order. This release
    # uses quilt's default -p1; reject other options rather than ignoring them.
    for line in ctx.read("debian/patches/series").splitlines():
        fields = [part for part in line.split("#", 1)[0].strip().replace("\t", " ").split(" ") if part]
        if not fields:
            continue
        if len(fields) != 1:
            fail("Unsupported Debian patch options: " + line)
        ctx.patch(ctx.path("debian/patches/" + fields[0]), strip = 1)

    # Preserve SONiC's debian/control and debian/rules changes as well as the
    # --enable-readline option used by the configure/Make target.
    ctx.patch(ctx.path(ctx.attr.readline_patch), strip = 1)
    # procan reports the compiler command as literal text; compiler prefix maps
    # cannot rewrite that metadata. Keep the real compile command unchanged.
    ctx.patch(ctx.path(ctx.attr.compiler_metadata_patch), strip = 1)
    # readlink() does not terminate the namespace path printed by procan.
    ctx.patch(ctx.path(ctx.attr.namespace_patch), strip = 1)
    ctx.symlink(ctx.attr.build_file, "BUILD.bazel")

socat_source = repository_rule(
    implementation = _socat_source_impl,
    attrs = {
        "upstream_urls": attr.string_list(mandatory = True),
        "upstream_sha256": attr.string(mandatory = True),
        "debian_urls": attr.string_list(mandatory = True),
        "debian_sha256": attr.string(mandatory = True),
        "readline_patch": attr.label(mandatory = True, allow_single_file = True),
        "compiler_metadata_patch": attr.label(default = "//:bazel/0002-compiler-metadata.patch", allow_single_file = True),
        "namespace_patch": attr.label(default = "//:bazel/0003-procan-namespace-nul.patch", allow_single_file = True),
        "build_file": attr.label(mandatory = True, allow_single_file = True),
    },
)
