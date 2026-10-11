# Distroless compatibility patches

`0.9.4.sonic.2` adds the shared infrastructure fix for empty pkg-config linker
arguments. Debian Abseil metadata uses repeated spaces; those must not create
empty input filenames when linking gRPC clients. Spaces and tabs separate
`Libs`, `Libs.private` and `Cflags` consistently.

The production patch is copied byte-for-byte from
[sonic-build-infra at 7755cb7](https://github.com/securely1g/sonic-build-infra/blob/7755cb7ee3efd0eb97d16721bb64c070141f6e96/third_party/rules_distroless/0001-pkgconfig-whitespace.patch).
The same Starlark regression is included in this entry's native AMD64 and ARM64
consumer tests, loading the parser from the published module. Upstream 0.9.4
remains the source archive, and the previous header fix is retained. Existing
published version directories are unchanged.

## Previous protobuf header fix

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
