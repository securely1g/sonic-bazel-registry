# sonic-mgmt-framework

Registry version `1.0.1-1ca814b6f0053fb728d40bfa82be69a4d4eca6bf` uses [the source snapshot](https://github.com/securely1g/sonic-mgmt-framework/tree/1ca814b6f0053fb728d40bfa82be69a4d4eca6bf) from `securely1g/sonic-mgmt-framework`. The source repository owns its build definitions and dependency pins; this entry adds the commit-qualified module identity and retained registry integration.

This exact source commit landed through [the owner change](https://github.com/securely1g/sonic-mgmt-framework/pull/3). Registry build/test acceptance is separate from source provenance.

```starlark
bazel_dep(
    name = "sonic-mgmt-framework",
    version = "1.0.1-1ca814b6f0053fb728d40bfa82be69a4d4eca6bf",
)
```

Current dependency versions are in [MODULE.bazel](MODULE.bazel). They select the published catalog at [`3d1cc5e8dfd5`](https://github.com/securely1g/sonic-bazel-registry/tree/3d1cc5e8dfd553d2acbe4198e504a245e6bdbddf).

The registry retains the published `go_mod` adaptation: Framework contributes `go.mod` dependencies, while the consuming root owns its Go workspace and replacements. The owner keeps `go.bazel.work` for standalone builds.

## Presubmit contract

The retained registry matrix selects: `amd64`. Platform mappings, additional architecture-specific targets and consumer settings are defined in [presubmit.json](presubmit.json). These declarations describe coverage, not a claim that CI passed.

Build targets:

```text
//:image_payload
@sonic-mgmt-framework//dist:runtime
@sonic-mgmt-framework//dist:runtime.debug_symbols
@sonic-mgmt-framework//dist:rest_binaries
@sonic-mgmt-framework//dist:ui
@sonic-mgmt-framework//CLI:runtime
@sonic-mgmt-framework//CLI:runtime.debug_symbols
```

Test targets:

```text
@sonic-mgmt-framework//dist:package_test
@sonic-mgmt-framework//dist:rest_runtime_test
@sonic-mgmt-framework//CLI:installed_runtime_test
@sonic-mgmt-framework//tools/bazel:models_repro_test
@sonic-mgmt-framework//tools/bazel:codegen_config_test
@sonic-mgmt-framework//rest/server:server_test
@sonic-mgmt-framework//tools/openapi_tests:generator_test
@sonic-mgmt-framework//CLI:cli_client_test
@sonic-mgmt-framework//CLI:generator_order_test
@sonic-mgmt-framework//CLI:rest_tls_test
```

The standalone consumer is [tests/consumer](tests/consumer).

Source archive integrity and the ordered patch/overlay inputs are recorded in [source.json](source.json). [Previous registration notes](https://github.com/securely1g/sonic-bazel-registry/blob/3d1cc5e8dfd553d2acbe4198e504a245e6bdbddf/modules/sonic-mgmt-framework/1.0.0-d48ffb1ebae56f6525f24e14d39562a0ba825daa/README.md) describe `1.0.0-d48ffb1ebae56f6525f24e14d39562a0ba825daa` and are historical rather than instructions for this version.
