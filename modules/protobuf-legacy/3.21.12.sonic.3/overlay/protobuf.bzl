"""Forward the public API to the Debian-prepared Protobuf source."""

load("@protobuf_source//:protobuf.bzl",
    _LegacyProtoInfo = "LegacyProtoInfo",
    _proto_gen = "proto_gen",
    _adapt_proto_library = "adapt_proto_library",
    _cc_proto_library = "cc_proto_library",
    _internal_gen_well_known_protos_java = "internal_gen_well_known_protos_java",
    _internal_gen_kt_protos = "internal_gen_kt_protos",
    _internal_copied_filegroup = "internal_copied_filegroup",
    _py_proto_library = "py_proto_library",
    _internal_protobuf_py_tests = "internal_protobuf_py_tests",
    _check_protobuf_required_bazel_version = "check_protobuf_required_bazel_version",
)

LegacyProtoInfo = _LegacyProtoInfo
proto_gen = _proto_gen
adapt_proto_library = _adapt_proto_library
cc_proto_library = _cc_proto_library
internal_gen_well_known_protos_java = _internal_gen_well_known_protos_java
internal_gen_kt_protos = _internal_gen_kt_protos
internal_copied_filegroup = _internal_copied_filegroup
py_proto_library = _py_proto_library
internal_protobuf_py_tests = _internal_protobuf_py_tests
check_protobuf_required_bazel_version = _check_protobuf_required_bazel_version
