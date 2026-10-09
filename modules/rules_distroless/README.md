# Distroless protobuf header imports

`0.9.4.sonic.1` registers upstream `rules_distroless` 0.9.4 with a fix for
protobuf headers imported from Debian packages. The importer must include
`usr/include/**/*.inc` in its C++ compilation inputs: public protobuf headers
include `port_def.inc` and `port_undef.inc`, so consumers fail to compile when
those fragments are missing from the Bazel sandbox.

Native AMD64 and ARM64 presubmits compile a real consumer of pinned Debian
Trixie protobuf headers through the importer's `CcInfo`. Two analysis tests also
check dependency-set selection for those CPUs. The fixture intentionally omits
runtime linker inputs; it validates the header import, not protobuf runtime
packaging. Test repositories are fetched only when their targets are used.

The dotted release suffix makes `0.9.4.sonic.1` sort above upstream `0.9.4`,
so a dependency requesting that upstream release does not displace the SONiC
patch. It also sorts above the previous `0.9.4-sonic.1` prerelease spelling.
Consumers should select `0.9.4.sonic.1` and verify the resolved module graph.
A root version override is unnecessary solely to win against those two versions;
it remains appropriate when the root deliberately needs an exact version pin.

The source archive, production patch and validation overlay are unchanged from
the published `0.9.4-sonic.1` entry. That entry and other published versions keep
their original contents. Closed, unmerged [PR #3](https://github.com/securely1g/sonic-bazel-registry/pull/3)
also used the dotted names in immutable branch snapshots; those snapshots remain
available, and consumers using them must verify the registry and selected entry.
