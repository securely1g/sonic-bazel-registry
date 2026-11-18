# sonic-py-swsssdk

Registry version `2.0.2-fff4c237b59329853f4fa72022c7e64d30794fdd` uses [the source snapshot](https://github.com/securely1g/sonic-py-swsssdk/tree/fff4c237b59329853f4fa72022c7e64d30794fdd) from `securely1g/sonic-py-swsssdk`. The source repository owns its build definitions and dependency pins; this entry adds the commit-qualified module identity and retained registry integration.

The pinned source is preserved on [the owner branch](https://github.com/securely1g/sonic-py-swsssdk/tree/codex/registry-deps-sonic-py-swsssdk-20261118) and is not yet landed. This registration must remain Draft until the source prerequisite lands.

```starlark
bazel_dep(
    name = "sonic-py-swsssdk",
    version = "2.0.2-fff4c237b59329853f4fa72022c7e64d30794fdd",
)
```

Current dependency versions are in [MODULE.bazel](MODULE.bazel). They select the published catalog at [`3d1cc5e8dfd5`](https://github.com/securely1g/sonic-bazel-registry/tree/3d1cc5e8dfd553d2acbe4198e504a245e6bdbddf).

The owner now supplies the Bazel build definitions. Its standalone consumer pins Bazel 8.5.1. The source preserves the ancestry of [the contributor build change](https://github.com/securely1g/sonic-py-swsssdk/pull/1); closing a follow-up PR does not land that contributor change.

## Presubmit contract

The retained registry matrix selects: `amd64`. Platform mappings, additional architecture-specific targets and consumer settings are defined in [presubmit.json](presubmit.json). These declarations describe coverage, not a claim that CI passed.

Build targets:

```text
@sonic-py-swsssdk//:swsssdk
@sonic-py-swsssdk//:swsssdk.wheel
@sonic-py-swsssdk//:swsssdk.runtime
@sonic-py-swsssdk//:swsssdk.runtime_metadata
```

Test targets:

```text
//:distribution_test
```

The standalone consumer is [tests/integration](tests/integration).

Source archive integrity and the ordered patch/overlay inputs are recorded in [source.json](source.json). [Previous registration notes](https://github.com/securely1g/sonic-bazel-registry/blob/3d1cc5e8dfd553d2acbe4198e504a245e6bdbddf/modules/sonic-py-swsssdk/2.0.1-5878f93779df1bfdfe58ea00c8d34fe8261d362e/README.md) describe `2.0.1-5878f93779df1bfdfe58ea00c8d34fe8261d362e` and are historical rather than instructions for this version.
