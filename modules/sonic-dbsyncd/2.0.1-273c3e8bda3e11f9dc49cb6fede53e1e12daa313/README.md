# sonic-dbsyncd

Registry version `2.0.1-273c3e8bda3e11f9dc49cb6fede53e1e12daa313` uses [the source snapshot](https://github.com/securely1g/sonic-dbsyncd/tree/273c3e8bda3e11f9dc49cb6fede53e1e12daa313) from `securely1g/sonic-dbsyncd`. The source repository owns its build definitions and dependency pins; this entry adds the commit-qualified module identity and retained registry integration.

This exact source commit landed through [the owner change](https://github.com/securely1g/sonic-dbsyncd/pull/3). Registry build/test acceptance is separate from source provenance.

```starlark
bazel_dep(
    name = "sonic-dbsyncd",
    version = "2.0.1-273c3e8bda3e11f9dc49cb6fede53e1e12daa313",
)
```

Current dependency versions are in [MODULE.bazel](MODULE.bazel). They select the published catalog at [`3d1cc5e8dfd5`](https://github.com/securely1g/sonic-bazel-registry/tree/3d1cc5e8dfd553d2acbe4198e504a245e6bdbddf).

## Presubmit contract

The retained registry matrix selects: `amd64`. Platform mappings, additional architecture-specific targets and consumer settings are defined in [presubmit.json](presubmit.json). These declarations describe coverage, not a claim that CI passed.

Build targets:

```text
@sonic-dbsyncd//:lldp_syncd
@sonic-dbsyncd//:sonic_syncd
@sonic-dbsyncd//:sonic_dbsyncd_wheel
@sonic-dbsyncd//:sonic_dbsyncd_runtime
```

Test targets:

```text
//:archive_contract_test
//:library_test
```

The standalone consumer is [tests/consumer](tests/consumer).

Source archive integrity and the ordered patch/overlay inputs are recorded in [source.json](source.json). [Previous registration notes](https://github.com/securely1g/sonic-bazel-registry/blob/3d1cc5e8dfd553d2acbe4198e504a245e6bdbddf/modules/sonic-dbsyncd/2.0.0-8a3830704d3f6067823f7c10b3b31913965add81/README.md) describe `2.0.0-8a3830704d3f6067823f7c10b3b31913965add81` and are historical rather than instructions for this version.
