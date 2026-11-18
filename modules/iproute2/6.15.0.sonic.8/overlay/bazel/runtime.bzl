load("@bazel_skylib//rules:select_file.bzl", "select_file")
load("@sonic_build_infra//binary:keep_debug_info.bzl", "keep_debug_info")
load("@sonic_build_infra//tar:sonic_deploy_tar.bzl", "sonic_deploy_tar")

def installed_file(name, subpath):
    """Select data from the same debug-preserving foreign build as the ELFs."""
    select_file(
        name = name + "_selected",
        srcs = ":iproute2_build",
        subpath = subpath,
        visibility = ["//visibility:private"],
    )
    # sonic_deploy_tar applies this transition to its ELF inputs. Apply the
    # identical transition to data/config inputs so Make only builds once.
    keep_debug_info(name = name, src = ":" + name + "_selected")

def runtime_for_arch(arch, triplet, programs, data_paths, installed_paths, netem):
    all_data = dict(data_paths)
    all_data.update(installed_paths)
    sonic_deploy_tar(
        name = "iproute2_pkg_" + arch,
        visibility = ["//visibility:private"],
        binaries = {path + " uid=0 gid=0 type=file mode=0755": ":built_" + name for name, path in programs.items()},
        force_debug_build = True,
        srcs = data_paths.keys() + installed_paths.keys() + [":installed_routel"] + [":" + name + "_distribution" for name in netem],
        mtree = [
            path + " uid=0 gid=0 type=file mode=0644 content=$(location " + source + ")"
            for source, path in all_data.items()
        ] + [
            "usr/bin/routel uid=0 gid=0 type=file mode=0755 content=$(location :installed_routel)",
            "usr/bin/ctstat uid=0 gid=0 type=link link=lnstat",
            "usr/bin/rtstat uid=0 gid=0 type=link link=lnstat",
            "usr/sbin/ip uid=0 gid=0 type=link link=../bin/ip",
        ] + ["usr/lib/" + triplet + "/tc/" + name + ".dist uid=0 gid=0 type=file mode=0644 content=$(location :" + name + "_distribution)" for name in netem],
    )
