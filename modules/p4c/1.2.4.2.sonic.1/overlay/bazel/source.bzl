"""Prepare the exact P4C source package selected by SONiC's P4 baseline."""

def _impl(ctx):
    ctx.download_and_extract(
        url = "https://github.com/securely1g/sonic-bazel-registry/releases/download/p4-source-inputs-20261021/p4lang-p4c_1.2.4.2.orig.tar.gz",
        sha256 = "a41d616add63924a098edaab446809f543ffadfc2e40356f9b73986f324c668a",
        type = "tar.gz",
    )
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
    for path in ['BUILD.bazel', 'build/_deps/protobuf-src/BUILD.bazel', 'build/_deps/p4runtime-src/proto/BUILD.bazel', 'build/_deps/p4runtime-src/bazel/example/BUILD.bazel', 'build/_deps/protobuf-src/csharp/BUILD.bazel', 'build/_deps/protobuf-src/build_defs/BUILD.bazel', 'build/_deps/protobuf-src/conformance/BUILD.bazel', 'build/_deps/protobuf-src/php/BUILD.bazel', 'build/_deps/protobuf-src/examples/BUILD.bazel', 'build/_deps/protobuf-src/ruby/BUILD.bazel', 'build/_deps/protobuf-src/util/python/BUILD.bazel', 'build/_deps/protobuf-src/third_party/googletest/BUILD.bazel', 'bazel/example/BUILD.bazel', 'bazel/example/p4/BUILD.bazel', 'backends/p4tools/BUILD.bazel']:
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
