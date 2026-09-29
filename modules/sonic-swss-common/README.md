# sonic-swss-common

## YANG-enabled release

`0.0.0-f15b4f87cff7379975f51917626d0f2a6c44614f` packages the merged
[Common source](https://github.com/securely1g/sonic-swss-common/commit/f15b4f87cff7379975f51917626d0f2a6c44614f)
from [Common PR #6](https://github.com/securely1g/sonic-swss-common/pull/6).
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
