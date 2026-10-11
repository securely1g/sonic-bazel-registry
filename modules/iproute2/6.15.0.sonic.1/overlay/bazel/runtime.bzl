load("@sonic_build_infra//tar:sonic_deploy_tar.bzl", "sonic_deploy_tar")

def runtime_for_arch(arch, triplet, programs, data_paths, netem):
    sonic_deploy_tar(
        name = "iproute2_pkg_" + arch,
        visibility = ["//visibility:private"],
        binaries = {path + " uid=0 gid=0 type=file mode=0755": ":built_" + name for name, path in programs.items()},
        force_debug_build = True,
        srcs = data_paths.keys() + ["ip/routel"] + [":" + name + "_distribution" for name in netem],
        mtree = [
            path + " uid=0 gid=0 type=file mode=0644 content=$(location " + source + ")"
            for source, path in data_paths.items()
        ] + [
            "usr/bin/routel uid=0 gid=0 type=file mode=0755 content=$(location ip/routel)",
            "usr/bin/ctstat uid=0 gid=0 type=link link=lnstat",
            "usr/bin/rtstat uid=0 gid=0 type=link link=lnstat",
            "usr/sbin/ip uid=0 gid=0 type=link link=../bin/ip",
        ] + ["usr/lib/" + triplet + "/tc/" + name + ".dist uid=0 gid=0 type=file mode=0644 content=$(location :" + name + "_distribution)" for name in netem],
    )
