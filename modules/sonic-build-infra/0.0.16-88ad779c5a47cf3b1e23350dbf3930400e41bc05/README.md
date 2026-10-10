# Shared OCI package inputs

This version lets [Buildimage #13](https://github.com/securely1g/sonic-buildimage/pull/13)
assemble Syncd-vs with the same image structure as SWSS. Its remaining Make DEBs
become ordinary declared Bazel inputs instead of a container-specific staging
protocol. Three shared features supply that adapter:

- [Infrastructure #30](https://github.com/securely1g/sonic-build-infra/pull/30)
  imports existing DEBs as ordered payload TARs with exact control metadata and
  original package hashes. It does not build DEBs or run maintainer scripts.
- [Infrastructure #31](https://github.com/securely1g/sonic-build-infra/pull/31)
  selects imported debug companions against the actual runtime image. For example,
  it retains the base's `libsonicdbcli` companion and DWZ supplement while
  excluding stale symbols for a Common library replaced by a source-built layer.
- [Infrastructure #32](https://github.com/securely1g/sonic-build-infra/pull/32)
  normalizes paths against the checked base's directory aliases. For example,
  `lib/example.so` becomes `usr/lib/example.so` without replacing `lib -> usr/lib`
  or changing an imported package's ownership.

The direct source prerequisite is #32, whose commit includes #30 and #31 through
its stacked base. This entry pins `88ad779c5a47cf3b1e23350dbf3930400e41bc05`,
with base module version `0.0.16`; the registry patch adds only its full source
commit suffix. The source stack is unmerged, so dependent PRs remain Draft.

Native AMD64/ARM64 presubmit retains the prior APT policy and dependency checks
and adds actual importer, normalizer and compiled-runtime symbol tests through
an independent Bazel consumer. Test DEBs are checked-in existing inputs; the
selected actions produce TARs, OCI fixtures and source binaries, never DEBs.
