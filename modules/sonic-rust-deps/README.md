# Shared SONiC Rust dependencies

## Exact native library artifacts

`0.0.4-6d9c70f708d7420e9e2b2cdc906b80cee6b140f1` registers the shared
module from [infra #38](https://github.com/securely1g/sonic-build-infra/pull/38).
The source-owned patch preserves exact ELF interface artifact paths during
ordinary rustc linking and uses actual runtime DSOs for loader search paths.
It adds no custom allocator and leaves Cargo dependency pins unchanged.

Native AMD64/ARM64 registry CI verifies this exact archive as an external
module. Tests cover shared Serde/tracing/supervisor dependencies and actual
Rust calls into versioned and non-lib-prefixed C++ shared libraries whose
interface artifacts share a basename. Both abort and unwind behavior are
checked. Source CI additionally runs optimized cross-crate full-LTO tests.
Every previously published registry entry is preserved.
