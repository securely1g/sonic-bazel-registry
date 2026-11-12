"""Prepare the exact P4C source package selected by SONiC's P4 baseline."""

def _impl(ctx):
    # The compiler itself comes directly from the primary upstream commit.
    ctx.download_and_extract(
        url = "https://codeload.github.com/p4lang/p4c/tar.gz/624c6be8076881e9af1e2f7d7691bc6c4416f4b1",
        sha256 = "8671a90b6ec252bde7f522f4b69f852e6b1e871e70df8e3815f82dacfb6e9394",
        stripPrefix = "p4c-624c6be8076881e9af1e2f7d7691bc6c4416f4b1",
        type = "tar.gz",
    )

    # GitHub archives omit submodule content. Restore the exact libbpf gitlink
    # recorded by the primary P4C commit from libbpf's upstream repository.
    ctx.download_and_extract(
        url = "https://codeload.github.com/libbpf/libbpf/tar.gz/051a4009f94d5633a8f734ca4235f0a78ee90469",
        sha256 = "274be7806056fefefa66d1dc1b2bcce5d4f60105916b9d9b40ca9547a3f8dce5",
        output = "backends/ebpf/runtime/contrib/libbpf",
        stripPrefix = "libbpf-051a4009f94d5633a8f734ca4235f0a78ee90469",
        type = "tar.gz",
    )

    # Recover only dependency inputs from the retained bundle. Its modified
    # compiler tree and old build directory never enter this repository.
    ctx.download_and_extract(
        url = "https://github.com/securely1g/sonic-bazel-registry/releases/download/p4-source-inputs-20261021/p4lang-p4c_1.2.4.2.orig.tar.gz",
        sha256 = "a41d616add63924a098edaab446809f543ffadfc2e40356f9b73986f324c668a",
        output = "build/_deps",
        stripPrefix = "build/_deps",
        type = "tar.gz",
    )
    for directory in ctx.path("build/_deps").readdir():
        if directory.basename not in ["protobuf-src", "p4runtime-src", "inja-src", "z3-src"]:
            ctx.delete(directory)

    # The selected Debian metadata replaces the older upstream packaging files.
    ctx.delete("debian")
    ctx.download_and_extract(
        url = "https://github.com/securely1g/sonic-bazel-registry/releases/download/p4-source-inputs-20261021/p4lang-p4c_1.2.4.2-3.debian.tar.xz",
        sha256 = "2a39bf04c8d084724014b71cdeb3b91dbe7a32bf1bd6cd499e5e132aa3e4cb40",
        type = "tar.xz",
    )
    if ctx.path("debian/patches/series").exists:
        for line in ctx.read("debian/patches/series").splitlines():
            fields = [x for x in line.split("#", 1)[0].strip().replace("\t", " ").split(" ") if x]
            if not fields:
                continue
            if len(fields) != 1:
                fail("Unsupported Debian patch options: " + line)
            ctx.patch(ctx.path("debian/patches/" + fields[0]), strip = 1)
    for patch in ctx.attr.patches:
        ctx.patch(ctx.path(patch), strip = 1)

    # This repository builds through upstream CMake. Remove Bazel package
    # boundaries so the declared source filegroup includes the bundled sources.
    for path in ["BUILD.bazel", "build/_deps/protobuf-src/BUILD.bazel", "build/_deps/p4runtime-src/proto/BUILD.bazel", "build/_deps/p4runtime-src/bazel/example/BUILD.bazel", "build/_deps/protobuf-src/csharp/BUILD.bazel", "build/_deps/protobuf-src/build_defs/BUILD.bazel", "build/_deps/protobuf-src/conformance/BUILD.bazel", "build/_deps/protobuf-src/php/BUILD.bazel", "build/_deps/protobuf-src/examples/BUILD.bazel", "build/_deps/protobuf-src/ruby/BUILD.bazel", "build/_deps/protobuf-src/util/python/BUILD.bazel", "build/_deps/protobuf-src/third_party/googletest/BUILD.bazel", "bazel/example/BUILD.bazel", "bazel/example/p4/BUILD.bazel", "backends/p4tools/BUILD.bazel"]:
        ctx.delete(path)

    for source, destination in ctx.attr.overlays.items():
        ctx.symlink(source, destination)

p4c_source = repository_rule(
    implementation = _impl,
    attrs = {
        "patches": attr.label_list(allow_files = True),
        "overlays": attr.label_keyed_string_dict(allow_files = True),
    },
)
