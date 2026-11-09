"""Select a small independent group without inventing package metadata."""

def _impl(rctx):
    document = json.decode(rctx.read(rctx.attr.lock))
    # Occupy the preferred internal catalog name as an ordinary public group.
    # Its only root is independent of the Lua/libc closure in the other groups.
    document["dependency_sets"]["apt_internal_package_catalog_0"] = {
        "sets": {
            arch: {key: version for key, version in roots.items() if key.split(":")[0].endswith("/netbase")}
            for arch, roots in document["dependency_sets"]["locked_import_ci"]["sets"].items()
        },
    }
    rctx.file("apt.lock.json", json.encode(document))
    rctx.file("BUILD.bazel", 'exports_files(["apt.lock.json"], visibility = ["//visibility:public"])\n')

shared_lock_fixture = repository_rule(
    implementation = _impl,
    attrs = {"lock": attr.label(mandatory = True, allow_single_file = [".json"])},
)
