"""Forward the public API to the Debian-prepared Protobuf source."""

load("@protobuf_source//:protobuf_deps.bzl",
    _PROTOBUF_MAVEN_ARTIFACTS = "PROTOBUF_MAVEN_ARTIFACTS",
    _protobuf_deps = "protobuf_deps",
)

PROTOBUF_MAVEN_ARTIFACTS = _PROTOBUF_MAVEN_ARTIFACTS
protobuf_deps = _protobuf_deps
