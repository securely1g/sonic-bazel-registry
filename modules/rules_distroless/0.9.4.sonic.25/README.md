# Share locked APT inputs across payloads, libraries and tools

`rules_distroless@0.9.4.sonic.17` adds the shared source/request and locked
import interfaces consumed by [build-infra #79](https://github.com/securely1g/sonic-build-infra/pull/79).
That source supplies `apt/sources.json`, `apt/requests.json` and
`apt/apt.lock.json` so package payloads, target headers/libraries and execution
tools can use the same reviewed package graph.

| Input or action | Published `.16` | This `.17` candidate |
| --- | --- | --- |
| Import shared source/request/lock files | The complete shared-input interface is unavailable | Resolve and import the reviewed package graph through the shared interface |
| Export static libraries, linker scripts and original DEBs | The additional export interface is unavailable | Preserve those inputs alongside native library and payload exports |
| Read exported pkg-config installation paths | Absolute paths refer to Debian's installation tree | Relocate exported standard variables relative to `pcfiledir` |
| Select Linux multiarch header roots | Select the configured target CPU's roots | Preserve the same target-CPU selection and AIO regression coverage |

Original Debian package archives remain unchanged. Patch 0020 provides the
additional interfaces and uses the declared AWK tool from
[gawk registry #204](https://github.com/securely1g/sonic-bazel-registry/pull/204).
The existing native header/library exports, symlink handling and package tests
remain part of the candidate.

## Inherited inputs and validation

Published `.16`, including registry #200's CPU-header fix, remains unchanged.
This candidate carries patches 0002–0019 forward byte-for-byte and changes
patch 0001 only to declare `.17`. It retains all eight build selections and
all 35 inherited tests, then adds the pkg-config relocation regression for
36 tests on each native AMD64 and ARM64 runner. The standalone integration
module selects `.17` and retains its package-lock and original-archive checks.
See [patch provenance](PATCHES.md).

The native AIO check still verifies `io_setup=206` on AMD64 and `io_setup=0`
on ARM64 and creates/destroys a real AIO context. The recipe imports existing
checksum-pinned packages; it adds no DEB producer. Source or registry tests do
not establish complete SONiC image acceptance.

The `.17` rebase requires fresh native validation; earlier `.16` candidate
results do not establish this revision's CI status. Before its prerequisites
land, use one pinned complete Draft-validation catalog alongside BCR. Normal
consumer defaults remain on the maintained registry branch.
