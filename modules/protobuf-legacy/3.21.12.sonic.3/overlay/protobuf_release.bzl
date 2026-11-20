"""Forward the public API to the Debian-prepared Protobuf source."""

load("@protobuf_source//:protobuf_release.bzl",
    _package_naming = "package_naming",
)

package_naming = _package_naming
