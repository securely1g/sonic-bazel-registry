# DASH HA native AMD64 source producer

This first registration uses [DASH HA source PR #1](https://github.com/securely1g/sonic-dash-ha/pull/1).
The source owns all 14 Cargo workspace crates, both original prost/tonic
generators, and the native install contract. Shared Rust crates, Common's Rust
library/testing interfaces, and HA's original API schema remain in their owners.
The only registry patch sets the commit-qualified module version.

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

This review entry depends on registry #198 (shared Rust), #201 (Common), #202
(API schema and metadata), and #195 (native metadata infrastructure). The root
consumer selects one coherent candidate set with the published Distroless .15
and tar.bzl 0.10.5-sonic.1. Docker integration is separate buildimage issue #128.
