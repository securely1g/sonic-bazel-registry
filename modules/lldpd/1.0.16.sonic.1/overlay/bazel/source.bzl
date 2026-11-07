"""Reconstruct the exact Debian and SONiC source without Debian packaging."""

def _series(text):
    result = []
    for line in text.splitlines():
        fields = [part for part in line.split("#", 1)[0].strip().replace("\t", " ").split(" ") if part]
        if not fields:
            continue
        if len(fields) != 1 or fields[0].startswith("/") or ".." in fields[0].split("/"):
            fail("Unsupported patch series entry: " + line)
        result.append(fields[0])
    return result

def _source_impl(ctx):
    ctx.download_and_extract(url = ctx.attr.upstream_url, sha256 = ctx.attr.upstream_sha256, stripPrefix = "lldpd-1.0.16")
    ctx.download_and_extract(url = ctx.attr.debian_url, sha256 = ctx.attr.debian_sha256)
    if not ctx.read("debian/changelog").startswith("lldpd (1.0.16-1+deb12u1)"):
        fail("Debian changelog does not match the selected SONiC lldpd source")
    for name in _series(ctx.read("debian/patches/series")):
        ctx.patch(ctx.path("debian/patches/" + name), strip = 1)
    patches = {ctx.path(label).basename: label for label in ctx.attr.sonic_patches}
    series = _series(ctx.read(ctx.attr.sonic_series))
    if sorted(patches.keys()) != sorted(series):
        fail("SONiC patch inputs differ from the maintained patch series")
    for name in series:
        ctx.patch(ctx.path(patches[name]), strip = 1)
    for source, destination in ctx.attr.overlays.items():
        ctx.symlink(source, destination)

lldpd_source = repository_rule(
    implementation = _source_impl,
    attrs = {
        "upstream_url": attr.string(mandatory = True),
        "upstream_sha256": attr.string(mandatory = True),
        "debian_url": attr.string(mandatory = True),
        "debian_sha256": attr.string(mandatory = True),
        "sonic_series": attr.label(allow_single_file = True, mandatory = True),
        "sonic_patches": attr.label_list(allow_files = True, mandatory = True),
        "overlays": attr.label_keyed_string_dict(allow_files = True, mandatory = True),
    },
)
