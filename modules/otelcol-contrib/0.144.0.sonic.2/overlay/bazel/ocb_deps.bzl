"""Keep upstream OCB tooling dependencies separate from collector runtime locks."""

load("@gazelle//:extensions.bzl", _go_deps = "go_deps")

go_deps = _go_deps
