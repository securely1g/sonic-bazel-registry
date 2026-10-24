"""Pair each deployed BMv2 ELF with the symbols from that same build."""

load("@bazel_skylib//rules:select_file.bzl", "select_file")
load("@sonic_build_infra//binary:keep_debug_info.bzl", "keep_debug_info")
load("@sonic_build_infra//tar:sonic_deploy_tar.bzl", "sonic_deploy_tar")

def installed_file(name, subpath):
    select_file(name = name + "_selected", srcs = ":bmv2_build", subpath = subpath, visibility = ["//visibility:private"])
    keep_debug_info(name = name, src = ":" + name + "_selected")

def runtime_for_arch(arch, triplet, programs, libraries, scripts, data_paths):
    for name in libraries:
        select_file(
            name = "built_" + name + "_" + arch,
            srcs = ":bmv2_build",
            subpath = "bmv2_build/usr/lib/" + triplet + "/" + name + ".so.0.0.0",
        )
    binaries = {"usr/bin/" + name + " uid=0 gid=0 type=file mode=0755": ":built_" + name for name in programs}
    binaries.update({
        "usr/lib/" + triplet + "/" + name + ".so.0.0.0 uid=0 gid=0 type=file mode=0644": ":built_" + name + "_" + arch
        for name in libraries
    })
    sonic_deploy_tar(
        name = "runtime_" + arch,
        binaries = binaries,
        force_debug_build = True,
        srcs = [":installed_" + path.replace("/", "_") for path in data_paths] + ["LICENSE", "debian/copyright"],
        mtree = [
            path + " uid=0 gid=0 type=file mode=" + ("0755" if path in ["usr/bin/" + s for s in scripts] else "0644") + " content=$(location :installed_" + path.replace("/", "_") + ")"
            for path in data_paths
        ] + [
            "usr/lib/" + triplet + "/" + name + ".so.0 uid=0 gid=0 type=link link=" + name + ".so.0.0.0"
            for name in libraries
        ] + [
            "usr/share/doc/p4lang-bmv2/LICENSE uid=0 gid=0 type=file mode=0644 content=$(location LICENSE)",
            "usr/share/doc/p4lang-bmv2/copyright uid=0 gid=0 type=file mode=0644 content=$(location debian/copyright)",
        ],
        visibility = ["//visibility:public"],
    )
