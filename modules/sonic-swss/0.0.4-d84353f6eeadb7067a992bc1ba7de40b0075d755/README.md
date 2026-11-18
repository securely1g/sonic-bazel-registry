# sonic-swss

Registry version `0.0.4-d84353f6eeadb7067a992bc1ba7de40b0075d755` uses [the source snapshot](https://github.com/securely1g/sonic-swss/tree/d84353f6eeadb7067a992bc1ba7de40b0075d755) from `securely1g/sonic-swss`. The source repository owns its build definitions and dependency pins; this entry adds the commit-qualified module identity and retained registry integration.

The pinned source is preserved on [the owner branch](https://github.com/securely1g/sonic-swss/tree/codex/registry-deps-sonic-swss-20261118) and is not yet landed. This registration must remain Draft until the source prerequisite lands.

```starlark
bazel_dep(
    name = "sonic-swss",
    version = "0.0.4-d84353f6eeadb7067a992bc1ba7de40b0075d755",
)
```

Current dependency versions are in [MODULE.bazel](MODULE.bazel). They select the published catalog at [`3d1cc5e8dfd5`](https://github.com/securely1g/sonic-bazel-registry/tree/3d1cc5e8dfd553d2acbe4198e504a245e6bdbddf).

The native build-contract guard records Infrastructure `0.0.38-0baa4acc9eac9ccc793b81104b1580d530271cbe`, matching the refreshed module pin. Strict compilation and linking checks remain enabled.

## Presubmit contract

The retained registry matrix selects: `amd64`, `arm64`. Platform mappings, additional architecture-specific targets and consumer settings are defined in [presubmit.json](presubmit.json). These declarations describe coverage, not a claim that CI passed.

Build targets:

```text
@sonic-swss//dist:cpp_binaries
@sonic-swss//dist:swss_pkg
@sonic-swss//dist:swss_pkg.debug_symbols
@sonic-swss//dist:runtime_packages.json
@sonic-swss//crates/countersyncd:countersyncd
@sonic-swss//dist:libteam_runtime
@sonic-swss//dist:libteam_debug
```

Test targets:

```text
@sonic-swss//gcovpreload:gcovpreload_test
@sonic-swss//bazel:protobuf_runtime_test
@sonic-swss//crates/countersyncd:common_rust_test
```

Source archive integrity and the ordered patch/overlay inputs are recorded in [source.json](source.json). [Previous registration notes](https://github.com/securely1g/sonic-bazel-registry/blob/3d1cc5e8dfd553d2acbe4198e504a245e6bdbddf/modules/sonic-swss/0.0.3-9c3797990d4b5a79100a40fe7689927c18212361/README.md) describe `0.0.3-9c3797990d4b5a79100a40fe7689927c18212361` and are historical rather than instructions for this version.
