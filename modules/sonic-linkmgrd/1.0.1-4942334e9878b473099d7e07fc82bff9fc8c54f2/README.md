# sonic-linkmgrd

Registry version `1.0.1-4942334e9878b473099d7e07fc82bff9fc8c54f2` uses [the source snapshot](https://github.com/securely1g/sonic-linkmgrd/tree/4942334e9878b473099d7e07fc82bff9fc8c54f2) from `securely1g/sonic-linkmgrd`. The source repository owns its build definitions and dependency pins; this entry adds the commit-qualified module identity and retained registry integration.

This exact source commit landed through [the owner change](https://github.com/securely1g/sonic-linkmgrd/pull/5). Registry build/test acceptance is separate from source provenance.

```starlark
bazel_dep(
    name = "sonic-linkmgrd",
    version = "1.0.1-4942334e9878b473099d7e07fc82bff9fc8c54f2",
)
```

Current dependency versions are in [MODULE.bazel](MODULE.bazel). They select the published catalog at [`3d1cc5e8dfd5`](https://github.com/securely1g/sonic-bazel-registry/tree/3d1cc5e8dfd553d2acbe4198e504a245e6bdbddf).

## Presubmit contract

The retained registry matrix selects: `amd64`. Platform mappings, additional architecture-specific targets and consumer settings are defined in [presubmit.json](presubmit.json). These declarations describe coverage, not a claim that CI passed.

Build targets:

```text
@sonic-linkmgrd//:linkmgrd
@sonic-linkmgrd//:sonic_linkmgrd_runtime
@sonic-linkmgrd//:sonic_linkmgrd_debug
@sonic-linkmgrd//:runtime_packages.json
```

Test targets:

```text
@sonic-linkmgrd//:linkmgrd_test
@sonic-linkmgrd//:source_contract_test
@sonic-linkmgrd//:package_test
```

The standalone consumer is [tests/consumer](tests/consumer).

Source archive integrity and the ordered patch/overlay inputs are recorded in [source.json](source.json). [Previous registration notes](https://github.com/securely1g/sonic-bazel-registry/blob/3d1cc5e8dfd553d2acbe4198e504a245e6bdbddf/modules/sonic-linkmgrd/1.0.0-92c78b468b678e3c2ed2877d2cb0a52306f2297f/README.md) describe `1.0.0-92c78b468b678e3c2ed2877d2cb0a52306f2297f` and are historical rather than instructions for this version.
