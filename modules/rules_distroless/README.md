# Distroless protobuf header imports

`0.9.4-sonic.1` registers upstream `rules_distroless` 0.9.4 with a fix for
protobuf headers imported from Debian packages. The importer must include
`usr/include/**/*.inc` in its C++ compilation inputs: public protobuf headers
include `port_def.inc` and `port_undef.inc`, so consumers fail to compile when
those fragments are missing from the Bazel sandbox.

Native AMD64 and ARM64 presubmits compile a real consumer of pinned Debian
Trixie protobuf headers through the importer's `CcInfo`. Two analysis tests also
check dependency-set selection for those CPUs. The fixture intentionally omits
runtime linker inputs; it validates the header import, not protobuf runtime
packaging. Test repositories are fetched only when their targets are used.

This entry carries forward the header fix and native tests from the closed
[PR #3](https://github.com/securely1g/sonic-bazel-registry/pull/3) using the current
version convention. Existing immutable registry snapshots remain available.
Consumers must update their module version and registry pin separately and
verify resolution: historical `0.9.4.sonic.*` versions sort above this new
hyphenated version, so changing a direct dependency alone may not select it.
