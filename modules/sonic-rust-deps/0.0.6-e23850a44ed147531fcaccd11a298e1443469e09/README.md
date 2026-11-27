# Shared Rust dependencies for DASH HA

DASH HA uses syn 3.0.10 and thiserror 2.0.21 for derive macros, and serde_serializer_quick_unsupported 1.0.1 for its SWSS serializer. The versioned Bazel targets preserve the earlier crate APIs for existing consumers. Registry CI builds both sets of targets with Rust 1.95 on AMD64 and ARM64 and exercises the derive, serializer and Host Services process APIs. [Build Infra #139](https://github.com/securely1g/sonic-build-infra/pull/139)

The container configuration daemon consumes epoll 4.4.0 and rustix 1.1.6 (fs and linux_5_11) from this graph. Its target and lock live with the shared module. The registry adds the source-qualified version and exercises its event and filesystem APIs on AMD64 and ARM64. [Build Infra #144](https://github.com/securely1g/sonic-build-infra/pull/144) · [Buildimage #31141](https://github.com/sonic-net/sonic-buildimage/pull/31141)
