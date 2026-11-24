# Shared Rust dependencies for DASH HA

DASH HA uses syn 3.0.10 and thiserror 2.0.21 for derive macros, and serde_serializer_quick_unsupported 1.0.1 for its SWSS serializer. The versioned Bazel targets preserve the earlier crate APIs for existing consumers. Registry CI builds both sets of targets with Rust 1.95 on AMD64 and ARM64 and exercises the derive, serializer and Host Services process APIs. [Build Infra #139](https://github.com/securely1g/sonic-build-infra/pull/139)
