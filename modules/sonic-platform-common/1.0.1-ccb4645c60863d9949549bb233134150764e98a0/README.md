# sonic-platform-common

Registry version `1.0.1-ccb4645c60863d9949549bb233134150764e98a0` uses [the source snapshot](https://github.com/securely1g/sonic-platform-common/tree/ccb4645c60863d9949549bb233134150764e98a0) from `securely1g/sonic-platform-common`. The source repository owns its build definitions and dependency pins; this entry adds the commit-qualified module identity and retained registry integration.

This exact source commit landed through [the owner change](https://github.com/securely1g/sonic-platform-common/pull/4). Registry build/test acceptance is separate from source provenance.

```starlark
bazel_dep(
    name = "sonic-platform-common",
    version = "1.0.1-ccb4645c60863d9949549bb233134150764e98a0",
)
```

Current dependency versions are in [MODULE.bazel](MODULE.bazel). They select the published catalog at [`3d1cc5e8dfd5`](https://github.com/securely1g/sonic-bazel-registry/tree/3d1cc5e8dfd553d2acbe4198e504a245e6bdbddf).

## Presubmit contract

The retained registry matrix selects: `amd64`. Platform mappings, additional architecture-specific targets and consumer settings are defined in [presubmit.json](presubmit.json). These declarations describe coverage, not a claim that CI passed.

Build targets:

```text
@sonic-platform-common//:sonic_platform_common_wheel
```

Test targets:

```text
//:installed_wheel_test
```

The standalone consumer is [tests/integration](tests/integration).

Source archive integrity and the ordered patch/overlay inputs are recorded in [source.json](source.json). [Previous registration notes](https://github.com/securely1g/sonic-bazel-registry/blob/3d1cc5e8dfd553d2acbe4198e504a245e6bdbddf/modules/sonic-platform-common/1.0.0/README.md) describe `1.0.0` and are historical rather than instructions for this version.
