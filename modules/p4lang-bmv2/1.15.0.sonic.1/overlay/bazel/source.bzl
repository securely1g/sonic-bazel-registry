"""Prepare the maintained BMv2 source without running Debian packaging."""

def _bmv2_source_impl(ctx):
    ctx.download_and_extract(url = ctx.attr.upstream_url, sha256 = ctx.attr.upstream_sha256, type = "tar.gz")
    ctx.download_and_extract(url = ctx.attr.debian_url, sha256 = ctx.attr.debian_sha256, type = "tar.xz")
    for line in ctx.read("debian/patches/series").splitlines():
        fields = [part for part in line.split("#", 1)[0].replace("\t", " ").split(" ") if part]
        if not fields:
            continue
        if len(fields) != 1:
            fail("Unsupported Debian patch options: " + line)
        ctx.patch(ctx.path("debian/patches/" + fields[0]), strip = 1)
    for patch in ctx.attr.sonic_patches:
        ctx.patch(ctx.path(patch), strip = 1)

    # Preserve get_version.sh's original archive identity without exposing .git
    # or an undeclared Git executable to the configure/build actions.
    revision = ctx.read(".git/HEAD").strip()
    if revision != "68f4a978f465fd76e98fcdecb762981843fb7310":
        fail("Unexpected BMv2 source archive revision: " + revision)
    ctx.file("VERSION-build", revision[:8] + "\n", executable = False)
    for source, destination in ctx.attr.overlays.items():
        ctx.symlink(source, destination)

bmv2_source = repository_rule(
    implementation = _bmv2_source_impl,
    attrs = {
        "upstream_url": attr.string(mandatory = True),
        "upstream_sha256": attr.string(mandatory = True),
        "debian_url": attr.string(mandatory = True),
        "debian_sha256": attr.string(mandatory = True),
        "sonic_patches": attr.label_list(allow_files = True),
        "overlays": attr.label_keyed_string_dict(mandatory = True, allow_files = True),
    },
)
