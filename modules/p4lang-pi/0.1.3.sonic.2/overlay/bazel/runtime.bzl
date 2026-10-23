load("@bazel_skylib//rules:select_file.bzl", "select_file")
load("@sonic_build_infra//tar:sonic_deploy_tar.bzl", "sonic_deploy_tar")
def installed_file(name, subpath):
    select_file(name = name, srcs = ":sdk", subpath = subpath)
def runtime_for_arch(arch, triplet, libraries, programs, python_files):
    binaries = {"usr/bin/" + name + " uid=0 gid=0 type=file mode=0755": ":built_" + name for name in programs}
    binaries.update({"usr/lib/" + triplet + "/lib" + name + ".so.0.0.0 uid=0 gid=0 type=file mode=0644": ":built_lib" + name for name in libraries})
    python = {":python_" + name.replace("/", "_"): "usr/lib/python3/dist-packages/" + name for name in python_files}
    sonic_deploy_tar(
        name = "runtime_" + arch,
        binaries = binaries,
        # configure_make always uses -g, disables linker stripping, and runs install.
        # The SDK already retains the DWARF needed by runtime/debug splitting.
        force_debug_build = False,
        srcs = python.keys() + ["LICENSE", "debian/copyright"],
        mtree = ["usr/lib/" + triplet + "/lib" + name + suffix + " uid=0 gid=0 type=link link=lib" + name + ".so.0.0.0" for name in libraries for suffix in [".so", ".so.0"]] +
                [path + " uid=0 gid=0 type=file mode=0644 content=$(location " + label + ")" for label, path in python.items()] + [
            "usr/share/doc/p4lang-pi/LICENSE uid=0 gid=0 type=file mode=0644 content=$(location LICENSE)",
            "usr/share/doc/p4lang-pi/copyright uid=0 gid=0 type=file mode=0644 content=$(location debian/copyright)",
        ],
        visibility = ["//visibility:public"],
    )
