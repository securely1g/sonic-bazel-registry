"""Five original CPython package layouts, with the actual default feature gate."""
load("@sonic_build_infra//tar:sonic_deploy_tar.bzl", "sonic_deploy_tar")

def python_runtime_tars(packages):
    for package, content in packages.items():
        mtree = []
        sources = []
        for path, row in content["files"].items():
            sources.append(row["label"])
            mtree.append("./" + path + " type=file uid=0 gid=0 mode=" + row["mode"] + " time=0 content=$(location " + row["label"] + ")")
        for path, destination in content["links"].items():
            mtree.append("./" + path + " type=link uid=0 gid=0 mode=0777 time=0 link=" + destination)
        for path in content["directories"]:
            mtree.append("./" + path + " type=dir uid=0 gid=0 mode=0755 time=0")
        binaries = {}
        for path, target in content["binaries"].items():
            # Original binary-arch dh_fixperms resets *.so and *.so.* to0644.
            mode = "0644" if ".so" in path.rsplit("/", 1)[-1] else "0755"
            binaries["./" + path + " type=file uid=0 gid=0 mode=" + mode + " time=0"] = target
        # Installation metadata is configured before the single TAR action.
        mtree = [row.replace("x86_64-linux-gnu", "{DEB_HOST_MULTIARCH}") for row in mtree]
        configured_binaries = {}
        for row, target in binaries.items():
            path, separator, attributes = row.partition(" type=")
            path = path.replace("x86_64-linux-gnu", "{DEB_HOST_MULTIARCH}")
            if "/lib-dynload/" in path and path.endswith(".so"):
                path = path[:-3] + ".cpython-313-{DEB_HOST_MULTIARCH}.so"
            configured_binaries[path + separator + attributes] = target
        sonic_deploy_tar(
            name = package + ".runtime",
            srcs = depset(sources).to_list(),
            mtree = mtree,
            binaries = configured_binaries,
            mtree_substitutions = select({
                "@platforms//cpu:x86_64": {"{DEB_HOST_MULTIARCH}": "x86_64-linux-gnu"},
                "@platforms//cpu:aarch64": {"{DEB_HOST_MULTIARCH}": "aarch64-linux-gnu"},
            }),
        )
