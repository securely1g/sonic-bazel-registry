## Registry dependency refresh: `0.0.6-2105715b2f6f186a41fd7f3e7522b94e8aac0bba`

Source: `securely1g/sonic-build-infra@2105715b2f6f186a41fd7f3e7522b94e8aac0bba`, based on `0baa4acc9eac9ccc793b81104b1580d530271cbe`. Dependency targets are frozen to published registry snapshot `3d1cc5e8dfd553d2acbe4198e504a245e6bdbddf`. The source owns the module base version and dependency updates. The registry supplies the full commit-qualified identity and retains its existing integration behavior.

Full archive patch-application and build validation must be recorded separately.

# sonic-rust-deps 0.0.5-5bf69bc0a7d9ea9f4a5606264be592867cd29d1e

Registers the fixed sonic-build-infra #110 first-parent source archive. Preserves the Rust 1.90.0 toolchain and existing five behavioral tests; adds native build coverage for the seven newly public crate aliases. Cargo.lock is taken unchanged from the source archive.

The original host-services Cargo.lock remains a separate dependency graph; this module does not replace it.
