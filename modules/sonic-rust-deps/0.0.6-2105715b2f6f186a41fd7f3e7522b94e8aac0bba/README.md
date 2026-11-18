# sonic-rust-deps

Registry version `0.0.6-2105715b2f6f186a41fd7f3e7522b94e8aac0bba` uses [the source snapshot](https://github.com/securely1g/sonic-build-infra/tree/2105715b2f6f186a41fd7f3e7522b94e8aac0bba) from `securely1g/sonic-build-infra`. The source repository owns its build definitions and dependency pins; this entry adds the commit-qualified module identity and retained registry integration.

The pinned source is preserved on [the owner branch](https://github.com/securely1g/sonic-build-infra/tree/codex/registry-deps-sonic-rust-deps-20261118) and is not yet landed. This registration must remain Draft until the source prerequisite lands.

```starlark
bazel_dep(
    name = "sonic-rust-deps",
    version = "0.0.6-2105715b2f6f186a41fd7f3e7522b94e8aac0bba",
)
```

Current dependency versions are in [MODULE.bazel](MODULE.bazel). They select the published catalog at [`3d1cc5e8dfd5`](https://github.com/securely1g/sonic-bazel-registry/tree/3d1cc5e8dfd553d2acbe4198e504a245e6bdbddf).

## Presubmit contract

The retained registry matrix selects: `amd64`, `arm64`. Platform mappings, additional architecture-specific targets and consumer settings are defined in [presubmit.json](presubmit.json). These declarations describe coverage, not a claim that CI passed.

Build targets:

```text
@sonic-rust-deps//:serde
@sonic-rust-deps//:serde_core
@sonic-rust-deps//tests:serde_roundtrip_test
@sonic-rust-deps//tests:tracing_test
@sonic-rust-deps//tests:supervisor_io_test
@sonic-rust-deps//tests:panic_runtime_test
@sonic-rust-deps//tests:dash_ha_contract_test
@sonic-rust-deps//:anyhow
@sonic-rust-deps//:atomic_enum
@sonic-rust-deps//:better-panic
@sonic-rust-deps//:bollard
@sonic-rust-deps//:contracts
@sonic-rust-deps//:dashmap
@sonic-rust-deps//:derivative
@sonic-rust-deps//:enumset
@sonic-rust-deps//:file-rotate
@sonic-rust-deps//:futures-core
@sonic-rust-deps//:futures-util
@sonic-rust-deps//:hex
@sonic-rust-deps//:human-panic
@sonic-rust-deps//:hyper-util
@sonic-rust-deps//:pretty_assertions
@sonic-rust-deps//:proc-macro2
@sonic-rust-deps//:prost-build
@sonic-rust-deps//:quote
@sonic-rust-deps//:serde_serializer_quick_unsupported
@sonic-rust-deps//:serde_with
@sonic-rust-deps//:signal-hook
@sonic-rust-deps//:strum
@sonic-rust-deps//:strum_macros
@sonic-rust-deps//:syn
@sonic-rust-deps//:tabled
@sonic-rust-deps//:tokio-util
@sonic-rust-deps//:tonic-build
@sonic-rust-deps//:tower
@sonic-rust-deps//:tracing-error
@sonic-rust-deps//:uuid
@sonic-rust-deps//:daemonize
@sonic-rust-deps//:pnet
@sonic-rust-deps//:procfs
@sonic-rust-deps//:psutil
@sonic-rust-deps//:regex
@sonic-rust-deps//:sysinfo
@sonic-rust-deps//:syslog
```

Test targets:

```text
@sonic-rust-deps//tests:serde_roundtrip_test
@sonic-rust-deps//tests:tracing_test
@sonic-rust-deps//tests:supervisor_io_test
@sonic-rust-deps//tests:panic_runtime_test
@sonic-rust-deps//tests:dash_ha_contract_test
```

Source archive integrity and the ordered patch/overlay inputs are recorded in [source.json](source.json). [Previous registration notes](https://github.com/securely1g/sonic-bazel-registry/blob/3d1cc5e8dfd553d2acbe4198e504a245e6bdbddf/modules/sonic-rust-deps/0.0.5-5bf69bc0a7d9ea9f4a5606264be592867cd29d1e/README.md) describe `0.0.5-5bf69bc0a7d9ea9f4a5606264be592867cd29d1e` and are historical rather than instructions for this version.
