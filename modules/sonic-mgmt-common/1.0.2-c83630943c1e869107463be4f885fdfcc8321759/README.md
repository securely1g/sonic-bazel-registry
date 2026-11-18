# sonic-mgmt-common

Registry version `1.0.2-c83630943c1e869107463be4f885fdfcc8321759` uses [the source snapshot](https://github.com/securely1g/sonic-mgmt-common/tree/c83630943c1e869107463be4f885fdfcc8321759) from `securely1g/sonic-mgmt-common`. The source repository owns its build definitions and dependency pins; this entry adds the commit-qualified module identity and retained registry integration.

This exact source commit landed through [the owner change](https://github.com/securely1g/sonic-mgmt-common/pull/6). Registry build/test acceptance is separate from source provenance.

```starlark
bazel_dep(
    name = "sonic-mgmt-common",
    version = "1.0.2-c83630943c1e869107463be4f885fdfcc8321759",
)
```

Current dependency versions are in [MODULE.bazel](MODULE.bazel). They select the published catalog at [`3d1cc5e8dfd5`](https://github.com/securely1g/sonic-bazel-registry/tree/3d1cc5e8dfd553d2acbe4198e504a245e6bdbddf).

## Presubmit contract

The retained registry matrix selects: `amd64`. Platform mappings, additional architecture-specific targets and consumer settings are defined in [presubmit.json](presubmit.json). These declarations describe coverage, not a claim that CI passed.

Build targets:

```text
//:consumer
@sonic-mgmt-common//cvl:cvl
@sonic-mgmt-common//translib:translib
@sonic-mgmt-common//translib/ocbinds:ocbinds
@sonic-mgmt-common//dist:runtime
@sonic-mgmt-common//dist:codegen
```

Test targets:

```text
@sonic-mgmt-common//dist:runtime_test
@sonic-mgmt-common//dist:codegen_contract_test
@sonic-mgmt-common//dist:schema_lint_test
@sonic-mgmt-common//dist:bindings_repro_test
@sonic-mgmt-common//tools/pyang:discovery_test
```

The standalone consumer is [tests/consumer](tests/consumer).

Source archive integrity and the ordered patch/overlay inputs are recorded in [source.json](source.json). [Previous registration notes](https://github.com/securely1g/sonic-bazel-registry/blob/3d1cc5e8dfd553d2acbe4198e504a245e6bdbddf/modules/sonic-mgmt-common/1.0.1-05f83dcab8fe2e1a0e0fc37ac172b289d6968e2b/README.md) describe `1.0.1-05f83dcab8fe2e1a0e0fc37ac172b289d6968e2b` and are historical rather than instructions for this version.
