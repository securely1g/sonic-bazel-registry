# Native component tools and installation TAR interfaces

This entry registers merged source commit
[`34de7330abc72229dfc8dab88dec71b89c52aa88`](https://github.com/securely1g/sonic-build-infra/commit/34de7330abc72229dfc8dab88dec71b89c52aa88)
from [build-infra #67](https://github.com/securely1g/sonic-build-infra/pull/67)
as `0.0.25-34de7330abc72229dfc8dab88dec71b89c52aa88`. It fetches the owning repository's archive directly and keeps
published `0.0.25-17a1e555291c64be1a6ff008f33352bffc4f8e5c` and every other
published entry unchanged.

[FRR #51](https://github.com/securely1g/sonic-buildimage/pull/51) needs shared
native-runtime execution for its `clippy_binary` code generator and installation
TAR interfaces that preserve its declared private-library search path. With
`preserve_install_rpath=True`, an installed FRR library retains
`/usr/lib/x86_64-linux-gnu/frr` while Bazel build-directory paths are removed.
[libteam #61](https://github.com/securely1g/sonic-buildimage/pull/61) uses the
source-owned runtime/TAR interfaces. Registering this version makes the merged
interfaces available; it does not update those consumers' selections.

## Source and patch provenance

Compared with published `0.0.25-17a1e555…`, the source archive advances from
[`17a1e555` to `34de7330`](https://github.com/securely1g/sonic-build-infra/compare/17a1e555291c64be1a6ff008f33352bffc4f8e5c...34de7330abc72229dfc8dab88dec71b89c52aa88).
The merged source selects published `rules_distroless@0.9.4.sonic.15`, including
the native APT exports and public Bazel 8 `cc_import` compatibility entry point.
Normal local and CI dependency defaults use maintained registry `main` and BCR.

Both inherited registry patches remain necessary. `0001-bump-version.patch`
adapts the source's `0.0.25` declaration to this registry version.
`0002-registry-cross-test-visibility.patch` remains byte-for-byte unchanged and
exposes the existing kernel cross-tool tests to the independent registry
consumer. Both apply with zero fuzz; no native-interface backport is needed.
The four existing overlays and their integrity values are unchanged.

The merged [registry #176](https://github.com/securely1g/sonic-bazel-registry/pull/176)
collector fix is inherited from maintained `main`, so native runtime trees with
Unicode certificate paths use ordinary CI. No collector or publication-policy
exception is added here. This registration adds no DEB package producer.

## Native validation

The presubmit retains all 32 build targets and 27 tests from the published
entry, plus the 13 native-interface tests already selected by this PR: **40 tests
on each of AMD64 and ARM64**. The additional coverage checks native runtime
execution, ORIGIN, RPATH/RUNPATH, source receipts, installation TARs, debug
ownership, compiler prefix mapping and Bookworm Perl/Valgrind/Tcl consumers.
The prefix-map fixture checks `DW_AT_comp_dir`, `DW_AT_name` and `__FILE__`
against the declared source execpath, including its external repository path.

Source #67 passed its native workflows before merging. This registry version
must separately pass its own independent-consumer matrix: source CI and the
previous registration's results do not substitute for registry validation.
See this PR's current checks for the final native results.
