# sonic-dhcpmon

Registry version `0.1.1-9941c86ae87437894fb76f3c10a0db863ba4d289` uses [the source snapshot](https://github.com/securely1g/sonic-dhcpmon/tree/9941c86ae87437894fb76f3c10a0db863ba4d289) from `securely1g/sonic-dhcpmon`. The source repository owns its build definitions and dependency pins; this entry adds the commit-qualified module identity and retained registry integration.

The pinned source is preserved on [the owner branch](https://github.com/securely1g/sonic-dhcpmon/tree/codex/registry-deps-sonic-dhcpmon-20261118) and is not yet landed. This registration must remain Draft until the source prerequisite lands.

```starlark
bazel_dep(
    name = "sonic-dhcpmon",
    version = "0.1.1-9941c86ae87437894fb76f3c10a0db863ba4d289",
)
```

Current dependency versions are in [MODULE.bazel](MODULE.bazel). They select the published catalog at [`3d1cc5e8dfd5`](https://github.com/securely1g/sonic-bazel-registry/tree/3d1cc5e8dfd553d2acbe4198e504a245e6bdbddf).

## Presubmit contract

The retained registry matrix selects: `amd64`, `arm64`. Platform mappings, additional architecture-specific targets and consumer settings are defined in [presubmit.json](presubmit.json). These declarations describe coverage, not a claim that CI passed.

Build targets:

```text
@sonic-dhcpmon//:runtime
@sonic-dhcpmon//:runtime.debug_symbols
@sonic-dhcpmon//:monitor_metadata
```

Test targets:

```text
@sonic-dhcpmon//:util_behavior_test
```

Source archive integrity and the ordered patch/overlay inputs are recorded in [source.json](source.json). [Previous registration notes](https://github.com/securely1g/sonic-bazel-registry/blob/3d1cc5e8dfd553d2acbe4198e504a245e6bdbddf/modules/sonic-dhcpmon/0.1.0-b824589b2ba49a8ba59142289bfb04bb3ca68875/README.md) describe `0.1.0-b824589b2ba49a8ba59142289bfb04bb3ca68875` and are historical rather than instructions for this version.
