"""Package installed P4C programs and data from one debug-preserving build."""
load("@bazel_skylib//rules:select_file.bzl", "select_file")
load("@sonic_build_infra//binary:keep_debug_info.bzl", "keep_debug_info")
load("@sonic_build_infra//tar:sonic_deploy_tar.bzl", "sonic_deploy_tar")

def p4c_runtime(programs, data):
    for program in programs:
        native.filegroup(name = "built_" + program, srcs = [":build"], output_group = program)
    for source, installed in data.items():
        name = "installed_" + source.replace("/", "_").replace(".", "_")
        select_file(name = name + "_selected", srcs = ":build", subpath = "p4c/" + installed)
        keep_debug_info(name = name, src = ":" + name + "_selected")
    native.filegroup(name = "built_p4testgen", srcs = [":build"], output_group = "p4testgen", target_compatible_with = ["@platforms//cpu:x86_64"])
    labels = {":installed_" + source.replace("/", "_").replace(".", "_"): path for source, path in data.items()}
    for cpu in ["x86_64", "aarch64"]:
        sonic_deploy_tar(
            name = "p4c_pkg_" + cpu,
            binaries = {"usr/bin/" + program + " uid=0 gid=0 type=file mode=0755": ":built_" + program for program in programs} | ({"usr/bin/p4testgen uid=0 gid=0 type=file mode=0755": ":built_p4testgen"} if cpu == "x86_64" else {}),
            force_debug_build = True,
            visibility = ["//visibility:public"],
            target_compatible_with = ["@platforms//cpu:" + cpu],
            srcs = labels.keys() + ["debian/copyright", "LICENSE"],
            mtree = [
                path + " uid=0 gid=0 type=file mode=" + ("0755" if path == "usr/bin/p4c" else "0644") + " content=$(location " + label + ")"
                for label, path in labels.items()
            ] + [
                "usr/share/doc/p4lang-p4c/copyright uid=0 gid=0 type=file mode=0644 content=$(location debian/copyright)",
                "usr/share/doc/p4lang-p4c/LICENSE uid=0 gid=0 type=file mode=0644 content=$(location LICENSE)",
            ],
        )
    for suffix in ["", ".debug_symbols"]:
        native.alias(name = "p4c_pkg" + suffix, actual = select({"@platforms//cpu:" + cpu: ":p4c_pkg_" + cpu + suffix for cpu in ["x86_64", "aarch64"]}))
    for name, filename in [("compile_commands", "compile_commands.json"), ("cmake_cache", "CMakeCache.txt")]:
        select_file(name = name + "_raw", srcs = ":build", subpath = "p4c/evidence/" + filename)
        keep_debug_info(name = name, src = ":" + name + "_raw")
    native.filegroup(name = "configuration", srcs = [":compile_commands", ":cmake_cache"])
