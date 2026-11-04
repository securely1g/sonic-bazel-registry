"""Keep original golden-test dependencies outside the collector runtime graph."""

load("@gazelle//:extensions.bzl", _go_deps = "go_deps")

go_deps = _go_deps
