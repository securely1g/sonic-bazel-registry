"""Keep release runtime dependencies separate from Bazel tool dependencies."""

load("@gazelle//:extensions.bzl", _go_deps = "go_deps")

go_deps = _go_deps
