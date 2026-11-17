# sonic-rust-deps 0.0.5-5bf69bc0a7d9ea9f4a5606264be592867cd29d1e

Registers the fixed sonic-build-infra #110 first-parent source archive. Preserves the Rust 1.90.0 toolchain and existing five behavioral tests; adds native build coverage for the seven newly public crate aliases. Cargo.lock is taken unchanged from the source archive.

The original host-services Cargo.lock remains a separate dependency graph; this module does not replace it.
