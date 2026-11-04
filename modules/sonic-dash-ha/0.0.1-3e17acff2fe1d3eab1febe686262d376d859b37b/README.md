# DASH HA native AMD64 source producer

This first registration uses [DASH HA source PR #1](https://github.com/securely1g/sonic-dash-ha/pull/1).
The source owns all 14 Cargo workspace crates, both original prost/tonic
generators, and the native install contract. Shared Rust crates, Common's Rust
library/testing interfaces, and HA's original API schema remain in their owners.
The registry MODULE patch sets the commit-qualified module version and aligns
the declared API and native infrastructure dependencies with the combined
consumer graph. Owner production source and Cargo inputs are unchanged.

The ordinary AMD64/Trixie consumer builds the runtime TAR, matching debug TAR,
source-package metadata and separate container utility. Its 20 original/installed
test targets cover all 19 HA test entrypoints plus strict installed TAR/ELF/debug
and private-loopback swbus acceptance. The source CI additionally tests Common's
three original async/testing interfaces in this same shared dependency graph.
The source driver proves optimized release builds; registry CI exercises its
ordinary external-consumer configuration. Neither path generates DEBs.

`Cargo.lock` remains canonical. The selected API owner exposes original schema
`18a29c1c8a21aeb22a4893c786564acaf8212156` with `ha_scope_id=1` and `vdpu_id=2`;
current API's reversed fields would change the HA wire contract. The original
HA generator remains unchanged.

This review entry uses registry #198 (shared Rust), the cumulative Common
registration #199, published API #202 at 9b2893e8, and infrastructure #218 at
2a6fc39c. Historical Common #201 closed without merging. The runtime source
and original HA schema contract remain unchanged; native/ordinary validation
of these aligned declarations is still required. Published Distroless .15 and
tar.bzl 0.10.5-sonic.1 declarations remain. Docker integration is separate
buildimage issue #128.
