# sonic-dash-ha

Registry version `0.0.2-9e0d2c9bd4ffb9d879a3bb86db0e80f2b86862f7` uses [the source snapshot](https://github.com/securely1g/sonic-dash-ha/tree/9e0d2c9bd4ffb9d879a3bb86db0e80f2b86862f7) from `securely1g/sonic-dash-ha`. The source repository owns its build definitions and dependency pins; this entry adds the commit-qualified module identity and retained registry integration.

The pinned source is preserved on [the owner branch](https://github.com/securely1g/sonic-dash-ha/tree/codex/registry-deps-sonic-dash-ha-20261118) and is not yet landed. This registration must remain Draft until the source prerequisite lands.

```starlark
bazel_dep(
    name = "sonic-dash-ha",
    version = "0.0.2-9e0d2c9bd4ffb9d879a3bb86db0e80f2b86862f7",
)
```

Current dependency versions are in [MODULE.bazel](MODULE.bazel). They select the published catalog at [`3d1cc5e8dfd5`](https://github.com/securely1g/sonic-bazel-registry/tree/3d1cc5e8dfd553d2acbe4198e504a245e6bdbddf).

## Presubmit contract

The retained registry matrix selects: `amd64`. Platform mappings, additional architecture-specific targets and consumer settings are defined in [presubmit.json](presubmit.json). These declarations describe coverage, not a claim that CI passed.

Build targets:

```text
@sonic-dash-ha//:dash_ha_pkg
@sonic-dash-ha//:dash_ha_pkg.debug_symbols
@sonic-dash-ha//:runtime_packages.json
@sonic-dash-ha//crates/container:container
```

Test targets:

```text
@sonic-dash-ha//crates/container:unit_test
@sonic-dash-ha//crates/hamgrd:unit_test
@sonic-dash-ha//crates/sonic-common:unit_test
@sonic-dash-ha//crates/sonic-dash-api-proto:unit_test
@sonic-dash-ha//crates/sonicdb-derive:basic_test
@sonic-dash-ha//crates/swbus-actor:echo_test
@sonic-dash-ha//crates/swbus-actor:kvstore_test
@sonic-dash-ha//crates/swbus-actor:test_executor_test
@sonic-dash-ha//crates/swbus-actor:unit_test
@sonic-dash-ha//crates/swbus-cli:unit_test
@sonic-dash-ha//crates/swbus-config:unit_test
@sonic-dash-ha//crates/swbus-core:basic_tests_test
@sonic-dash-ha//crates/swbus-core:inter_cluster_tests_test
@sonic-dash-ha//crates/swbus-core:unit_test
@sonic-dash-ha//crates/swbus-edge:unit_test
@sonic-dash-ha//crates/swbus-proto:unit_test
@sonic-dash-ha//crates/swbusd:unit_test
@sonic-dash-ha//crates/swss-common-bridge:unit_test
@sonic-dash-ha//crates/swss-serde:unit_test
@sonic-dash-ha//bazel:installed_package_test
@sonic-dash-ha//crates/swbus-actor:doc_test
```

Source archive integrity and the ordered patch/overlay inputs are recorded in [source.json](source.json). [Previous registration notes](https://github.com/securely1g/sonic-bazel-registry/blob/3d1cc5e8dfd553d2acbe4198e504a245e6bdbddf/modules/sonic-dash-ha/0.0.1-502377912f3530c9bb6c27007822919f6f32aeb7/README.md) describe `0.0.1-502377912f3530c9bb6c27007822919f6f32aeb7` and are historical rather than instructions for this version.
