"""Forward the public API to the Debian-prepared Protobuf source."""

load("@protobuf_source//:defs.bzl",
    _cpp_proto_sources = "cpp_proto_sources",
    _python_proto_sources = "python_proto_sources",
)

cpp_proto_sources = _cpp_proto_sources
python_proto_sources = _python_proto_sources
