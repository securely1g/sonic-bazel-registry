# rules_go

## 0.64.1-sonic.1

Uses the official rules_go 0.64.1 release archive and backports the missing
relative-header handling from [upstream #4583](https://github.com/bazel-contrib/rules_go/pull/4583).
On Bazel 8.5.1, an external `cc_import` can expose `include` without its
repository prefix. The patch combines that directory with the repository
roots so cgo can find the header, including with `external_include_paths`.
It keeps the external-include forwarding and linker fixes already upstream.

Registry CI runs the original two build regression cases on native AMD64 and
ARM64 with Bazel 8.5.1. The test API is adapted from `WorkspaceSuffix` to
`ModuleFileSuffix`/`use_repo_rule`; the original fixtures and test bodies are
unchanged. These tests compile and link a cgo consumer; they do not run it.
Registry CI uses upstream's default Go SDK (1.26.7). The separate comparison
experiment pins Go 1.25.0, matching the unpatched baseline.

The new version is a prerelease in Bazel's ordering. A root consumer needing
this fix should enforce it when another dependency requests plain 0.64.1:

```starlark
bazel_dep(name = "rules_go", version = "0.64.1-sonic.1")
single_version_override(module_name = "rules_go", version = "0.64.1-sonic.1")
```

Published 0.60.0.sonic-patched remains unchanged for existing consumers.
