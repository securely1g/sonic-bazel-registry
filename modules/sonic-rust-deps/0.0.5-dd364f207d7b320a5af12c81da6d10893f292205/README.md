# Shared Rust dependencies for DASH HA

This registers [infra #78](https://github.com/securely1g/sonic-build-infra/pull/78)
for [DASH HA source conversion](https://github.com/securely1g/sonic-buildimage/issues/104).
HA's fourteen crates, original prost/tonic generators and Common-owned Rust
interfaces use one third-party graph. Source compilation and installed runtime/debug
TAR validation remain with `sonic-dash-ha`; this module owns only external crates.

The `.4` build targets and tests are retained. Five native consumer tests exercise
shared Serde traits, tracing, supervisor I/O, panic/unwind native runtime linking,
and HA protocol/state/cancellation interfaces. All thirty added public crate
interfaces are explicit build targets on both existing architectures. Source CI
also retains its full-LTO panic test and verifies unchanged canonical Cargo.lock.

The deliberate compatibility change selects HA's original tokio-util 0.7.14 in
place of 0.7.17. HA enables `rt`; the latter version imports newer Tokio APIs when
that feature is active, while retained OpenTelemetry 0.25 requires Tokio ~1.38.0.
Tokio remains 1.38.2. Every other prior package identity/checksum is preserved;
new dependencies start from HA's original lock. The source README and
`dash_ha_contract_test` document and exercise the actual cancellation contract.
