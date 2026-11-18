# sonic-yang-models

Registry version `1.0.2-1dbe7ad4ab7efab414537236eb2f8522ce1f8abd` uses [the source snapshot](https://github.com/securely1g/sonic-buildimage/tree/1dbe7ad4ab7efab414537236eb2f8522ce1f8abd) from `securely1g/sonic-buildimage`. The source repository owns its build definitions and dependency pins; this entry adds the commit-qualified module identity and retained registry integration.

The pinned source is preserved on [the owner branch](https://github.com/securely1g/sonic-buildimage/tree/codex/registry-deps-sonic-yang-models-20261118) and is not yet landed. This registration must remain Draft until the source prerequisite lands.

```starlark
bazel_dep(
    name = "sonic-yang-models",
    version = "1.0.2-1dbe7ad4ab7efab414537236eb2f8522ce1f8abd",
)
```

Current dependency versions are in [MODULE.bazel](MODULE.bazel). They select the published catalog at [`3d1cc5e8dfd5`](https://github.com/securely1g/sonic-bazel-registry/tree/3d1cc5e8dfd553d2acbe4198e504a245e6bdbddf).

The source-owned model package exposes the runtime metadata provider consumed by YANG management. The registry retains its existing model, wheel and package entry points.

## Presubmit contract

The retained registry matrix selects: `amd64`, `arm64`. Platform mappings, additional architecture-specific targets and consumer settings are defined in [presubmit.json](presubmit.json). These declarations describe coverage, not a claim that CI passed.

Build targets:

```text
@sonic-yang-models//:yang_models
@sonic-yang-models//:yang_models_wheel
@sonic-yang-models//:yang_models_pkg
```

Test targets:

```text
@sonic-yang-models//:yang_models_package_test
```

Source archive integrity and the ordered patch/overlay inputs are recorded in [source.json](source.json). [Previous registration notes](https://github.com/securely1g/sonic-bazel-registry/blob/3d1cc5e8dfd553d2acbe4198e504a245e6bdbddf/modules/sonic-yang-models/1.0.1-b0a9362a7a1b4b5e1b7188c019d256f7c8aaff9f/README.md) describe `1.0.1-b0a9362a7a1b4b5e1b7188c019d256f7c8aaff9f` and are historical rather than instructions for this version.
