# sonic-swss-common

## Common-owned Rust library

`0.0.1-4150597fee0c644334613a5b2a8ef73fc7cb3d76` registers
[Common PR #17](https://github.com/securely1g/sonic-swss-common/pull/17) for
[SWSS PR #2](https://github.com/securely1g/sonic-swss/pull/2). The public
`//crates/swss-common:swss_common` target builds the Rust library, generated FFI
bindings and native Common library from one source revision. Public `serde` and
`serde_core` aliases let consumers share the crate identities used by Common's
Rust API. The source repository owns the build definitions and committed
`Cargo.lock`; `Cargo.Bazel.lock` is generated during build preparation and is
absent from the source archive. This entry carries only a module-version patch. Common declares base version
`0.0.1`, so this release sorts above the older `0.0.0` dependencies requested
transitively by SWSS.

The registry matrix retains nine C++/YANG, Python, Go and tar build targets and
ten runtime/package tests on native AMD64 and ARM64 with YANG enabled. It does
not build the Rust library: the registry's test root does not configure Rust
and bindgen toolchains. Common's source CI selects the Rust library and four
service-free unit tests with YANG enabled and disabled; SWSS's native CI checks
the downstream countersyncd build and its runtime/debug archives. These source
and consumer checks establish the Rust integration separately from registry CI.

Before loading Rust targets, downstream roots prepare a private writable copy
of the selected Common source with its pinned preparation helper and provide
compatible Rust and bindgen toolchains. SWSS's preparation command stages its
declared Common version automatically; buildimage prepares its recorded Common
checkout first. The C++/YANG registry matrix does not evaluate the crates
extension or require generated Rust metadata. Each consumer verifies its
resolved Common version. Existing published versions remain unchanged. This
candidate depends on the unlanded source commit in Common PR #17 and remains
Draft until that source provenance is updated and verified after landing.

## Common-owned Rust binding interface

`0.0.0-120a955096bb18413d170d42b30668dc7a9b7f68` packages the
[merged Common source](https://github.com/securely1g/sonic-swss-common/commit/120a955096bb18413d170d42b30668dc7a9b7f68)
from [Common PR #11](https://github.com/securely1g/sonic-swss-common/pull/11).
It retains the external YANG fixture fix from the prior registration and adds
`//crates/swss-common:bindings_dir`, which generates the Rust FFI bindings from
the C API headers in the same Common source revision. The source repository
owns this interface; this registry entry changes only the module version.

The native AMD64 and ARM64 registry matrix retains the existing C++/YANG,
Python, Go, and package validation described below, with Common's infrastructure
`0.0.6-553b2f70f9ba77b74befdf77674894166139ddcc` test pin. It does not
select the Rust binding target. Common's source CI separately generates bindings
on native AMD64 and ARM64 with YANG enabled and disabled. A downstream root that
selects `bindings_dir` supplies its own Rust and bindgen toolchains and must
validate the generated API and matching Rust/native source revisions; the
registry matrix does not establish that consumer integration.

This replaces the unmerged draft entry based on `36048b92907c21a5ef762eaa60a86e073e743dd0`.
The prior immutable registry snapshot
[`43576c0`](https://github.com/securely1g/sonic-bazel-registry/commit/43576c0208dc3dade1406f51f0a34e84bac67943)
retains that entry unchanged. Already published versions on `main` are preserved.

## YANG-enabled release

`0.0.0-5ee19a9375e667c0d507239927745de8fa29be07` packages the
[Common source](https://github.com/securely1g/sonic-swss-common/commit/5ee19a9375e667c0d507239927745de8fa29be07)
from merged [Common PR #9](https://github.com/securely1g/sonic-swss-common/pull/9),
based on merged [Common PR #6](https://github.com/securely1g/sonic-swss-common/pull/6).
The source revision fixes the YANG test fixture paths when Common is an external
dependency; the source repository owns that fix.
Common owns its Bazel targets and tests. This registry entry changes only its
module version to identify the exact source commit. Historical published
versions retain their original contents.

The default build enables YANG generation using the source-built libyang module,
shared SONiC YANG models and management modules, and their Python binding. It
uses native build infrastructure
`0.0.6-553b2f70f9ba77b74befdf77674894166139ddcc`. The existing
`libnl3 3.7.0.sonic-buildimage` dependency remains selected; this registration
does not substitute the newer AMD64-only validated libnl3 overlay.

### Registry validation

The version's `presubmit.json` validates the module from a separate consumer on
native AMD64 and ARM64 Debian Trixie with Bazel 8.5.1. It leaves the YANG build
setting at its enabled default and explicitly builds schema generation, the C++
library and tool, Python and Go bindings, runtime packages, and the matching
library debug-symbol package.

Ten source-owned tests cover service-free C++ behavior, the dynamic C API
consumer, YANG defaults, extracted library/debug and Python package contracts,
and the Go runtime consumer. Registry CI runs these tests without cached test
results and retains the generated consumer, fetched module declarations,
packages, hashes, and validation logs. Its test consumer pins the declared
infrastructure version exactly; downstream roots must validate their own
resolved graph.

The source repository separately covers the no-YANG configuration. This registry
matrix covers native AMD64 and ARM64 with YANG enabled; it does not establish
ARMHF, Redis-dependent tests, Debian package equivalence, or installed SONiC
container/image behavior.

## No-YANG release: 0.0.0-99572f5a34e7f408dee49eaf2a3ba60c5d443fb6

This release fetches the merged Common source at
[`99572f5`](https://github.com/securely1g/sonic-swss-common/commit/99572f5a34e7f408dee49eaf2a3ba60c5d443fb6).
Common owns its Bazel build and migration history. The registry carries only a
patch to the module version, matching the source commit named by the release.

This replaces the draft `0.0.0-10d14ae58ae73899a52a2447d1e791a2b7bd1a34` entry,
which applied the entire Bazel migration to an older source archive. That draft
entry has been removed from the current index. Its already-published immutable
registry snapshots (including `ab3d2af909a4791bdc53d3aa48005c36cb7d528a` and
`3131031ad639e33a6a99599b954863f9e9f62532`) retain exactly their original contents
for historical consumers. SWSS advances both its Common version and registry
pin together; there is no in-place change to the old module's source or hashes.

### Registry CI

The version's `presubmit.json` selects the source repository's supported no-YANG
configuration on native AMD64 and ARM64 Debian Trixie. It builds the C++ library
and tool, Python and Go bindings, runtime packages, and matching detached debug
symbols through explicit required targets. The seven explicit source-owned tests
include the dynamic C API runtime test and the package layout and debug-symbol
checks.

The manifest adds no test-only dependencies to the published module. Registry CI
uses a separate `registry_ci_consumer` root and pins the infrastructure version
in `consumer_deps` exactly. It verifies the fetched dependency's module name and
version and retains that declaration with the validation artifacts. Standalone
and downstream builds use their own root-module configuration.
