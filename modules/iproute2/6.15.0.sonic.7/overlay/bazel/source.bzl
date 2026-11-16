"""Assemble iproute2's Debian source package without invoking Debian packaging."""

def _iproute2_source_impl(ctx):
    ctx.download_and_extract(
        url = ctx.attr.upstream_url,
        sha256 = ctx.attr.upstream_sha256,
        stripPrefix = "iproute2-6.15.0",
    )
    ctx.download_and_extract(
        url = ctx.attr.debian_url,
        sha256 = ctx.attr.debian_sha256,
    )

    # The Debian archive owns the patch inventory and its application order.
    # This version uses quilt's default -p1; fail if a future series needs
    # other options instead of silently applying it with different semantics.
    for line in ctx.read("debian/patches/series").splitlines():
        fields = [part for part in line.split("#", 1)[0].strip().replace("\t", " ").split(" ") if part]
        if not fields:
            continue
        if len(fields) != 1:
            fail("Unsupported Debian patch options: " + line)
        ctx.patch(ctx.path("debian/patches/" + fields[0]), strip = 1)
    ctx.patch(ctx.path(ctx.attr.sonic_patch), strip = 1)

    # Match src/iproute2/Makefile's changelog update. Read its three version
    # assignments from the pinned existing rules file rather than maintaining
    # another package version in this Bazel overlay.
    versions = {}
    for line in ctx.read(ctx.attr.version_recipe).splitlines():
        fields = line.split("=", 1)
        if len(fields) != 2:
            continue
        key, value = fields[0].strip(), fields[1].strip()
        if key not in ["IPROUTE2_VERSION_BASE", "IPROUTE2_DEBIAN_VERSION", "IPROUTE2_VERSION_FULL"]:
            continue
        for name, version in versions.items():
            value = value.replace("$(" + name + ")", version)
        if "$" in value or not value or key in versions:
            fail("Unsupported iproute2 version recipe: " + line)
        versions[key] = value
    if len(versions) != 3:
        fail("The SONiC iproute2 recipe must declare all three version values")
    changelog = ctx.read("debian/changelog")
    original = "(" + versions["IPROUTE2_DEBIAN_VERSION"] + ")"
    if original not in changelog.splitlines()[0]:
        fail("Debian iproute2 changelog differs from the SONiC source recipe")
    ctx.file("debian/changelog", changelog.replace(original, "(" + versions["IPROUTE2_VERSION_FULL"] + ")", 1), executable = False)

    # Declare the build integration alongside the complete prepared source tree.
    for source, destination in ctx.attr.overlays.items():
        ctx.symlink(source, destination)

iproute2_source = repository_rule(
    implementation = _iproute2_source_impl,
    attrs = {
        "upstream_url": attr.string(mandatory = True),
        "upstream_sha256": attr.string(mandatory = True),
        "debian_url": attr.string(mandatory = True),
        "debian_sha256": attr.string(mandatory = True),
        "version_recipe": attr.label(mandatory = True, allow_single_file = True),
        "sonic_patch": attr.label(mandatory = True, allow_single_file = True),
        "overlays": attr.label_keyed_string_dict(mandatory = True, allow_files = True),
    },
)
