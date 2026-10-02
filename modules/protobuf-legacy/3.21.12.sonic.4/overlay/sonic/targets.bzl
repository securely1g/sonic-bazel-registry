"""Shared-only consumer interface and deployment packages for upstream Protobuf."""

load("@rules_cc//cc:defs.bzl", "cc_binary", "cc_import", "cc_library")
load("@rules_python//python:defs.bzl", "py_test")
load("@sonic_build_infra//tar:sonic_deploy_tar.bzl", "sonic_deploy_tar")
load("//:defs.bzl", "cpp_proto_sources", "python_proto_sources")

def sonic_targets():
    """Add shared runtime and native consumer tests without replacing upstream targets."""
    public = ["//visibility:public"]
    for cpu in ["x86_64", "aarch64"]:
        native.config_setting(name = "sonic_" + cpu, constraint_values = ["@platforms//cpu:" + cpu])
    cc_binary(
        name = "libprotobuf.so.32",
        linkshared = True,
        linkstatic = True,
        features = ["-sonic_installed_runtime_paths"],
        linkopts = [
            "-Wl,-soname,libprotobuf.so.32",
            "-Wl,--build-id=sha1",
            "-Wl,--exclude-libs,libzlib.a:libzlib.pic.a",
        ],
        deps = [":protobuf"],
        visibility = public,
    )
    native.alias(name = "shared_library", actual = ":libprotobuf.so.32", visibility = public)

    # A cc_import has no static archive, including when its consumer sets linkstatic.
    cc_import(name = "protobuf_shared", shared_library = ":libprotobuf.so.32")
    cc_library(name = "libprotobuf", deps = [":protobuf_shared", ":protobuf_headers"], visibility = public)
    native.alias(name = "libprotobuf_runtime_file", actual = ":shared_library", visibility = public)
    for cpu, multiarch in [("x86_64", "x86_64-linux-gnu"), ("aarch64", "aarch64-linux-gnu")]:
        sonic_deploy_tar(
            name = "libprotobuf_pkg_" + cpu,
            srcs = ["LICENSE"],
            binaries = {"usr/lib/{}/libprotobuf.so.32.0.12 uid=0 gid=0 type=file mode=0644".format(multiarch): ":libprotobuf.so.32"},
            force_debug_build = True,
            mtree = [
                "usr/lib/{}/libprotobuf.so.32 uid=0 gid=0 type=link link=libprotobuf.so.32.0.12".format(multiarch),
                "usr/share/doc/protobuf-legacy/copyright uid=0 gid=0 type=file mode=0644 content=$(location LICENSE)",
            ],
            target_compatible_with = ["@platforms//cpu:" + cpu],
            visibility = public,
        )
    for suffix in ["", ".debug_symbols"]:
        native.alias(name = "libprotobuf_pkg" + suffix, actual = select({":sonic_" + cpu: ":libprotobuf_pkg_" + cpu + suffix for cpu in ["x86_64", "aarch64"]}), visibility = public)
    cpp_proto_sources(name = "probe_generated", srcs = ["probe.proto"], output_prefix = "generated", visibility = public)
    native.filegroup(name = "probe_sources", srcs = [":probe_generated"], output_group = "sources")
    native.filegroup(name = "probe_headers", srcs = [":probe_generated"], output_group = "headers")
    cc_library(name = "probe", srcs = [":probe_sources"], hdrs = [":probe_headers"], includes = ["generated"], deps = [":libprotobuf"])
    cc_binary(name = "generated_runtime_consumer", srcs = ["//bazel:generated_runtime_consumer.cc"], linkopts = ["-ldl"], deps = [":probe"], visibility = public)
    py_test(
        name = "generated_runtime_test",
        srcs = ["//bazel:generated_runtime_test.py"],
        main = "//bazel:generated_runtime_test.py",
        args = ["--consumer=$(rlocationpath :generated_runtime_consumer)", "--library=$(rlocationpath :shared_library)"] + select({":sonic_x86_64": ["--architecture=amd64"], ":sonic_aarch64": ["--architecture=arm64"]}),
        data = [":generated_runtime_consumer", ":shared_library"],
        deps = ["@rules_python//python/runfiles"],
        visibility = public,
    )
    python_proto_sources(name = "probe_python", srcs = ["probe.proto"], output_prefix = "generated", visibility = public)
    py_test(
        name = "generated_python_test",
        srcs = ["//bazel:generated_python_test.py"],
        main = "//bazel:generated_python_test.py",
        args = ["$(rlocationpath :generated/probe_pb2.py)", "$(rlocationpath :generated/probe_pb2.pyi)"],
        data = [":generated/probe_pb2.py", ":generated/probe_pb2.pyi"],
        deps = ["@rules_python//python/runfiles"],
        visibility = public,
    )

    py_test(
        name = "source_package_test",
        srcs = ["//bazel:source_package_test.py"],
        main = "//bazel:source_package_test.py",
        args = [
            "--runtime=$(rlocationpath :libprotobuf_pkg)",
            "--debug=$(rlocationpath :libprotobuf_pkg.debug_symbols)",
            "--consumer=$(rlocationpath :generated_runtime_consumer)",
            "--protoc=$(rlocationpath :protoc)",
        ],
        data = [":libprotobuf_pkg", ":libprotobuf_pkg.debug_symbols", ":generated_runtime_consumer", ":protoc"],
        deps = ["@rules_python//python/runfiles"],
        visibility = public,
    )
