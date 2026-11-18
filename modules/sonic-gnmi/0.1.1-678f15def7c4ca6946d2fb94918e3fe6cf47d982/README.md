# sonic-gnmi

Registry version `0.1.1-678f15def7c4ca6946d2fb94918e3fe6cf47d982` uses [the source snapshot](https://github.com/securely1g/sonic-gnmi/tree/678f15def7c4ca6946d2fb94918e3fe6cf47d982) from `securely1g/sonic-gnmi`. The source repository owns its build definitions and dependency pins; this entry adds the commit-qualified module identity and retained registry integration.

The pinned source is preserved on [the owner branch](https://github.com/securely1g/sonic-gnmi/tree/codex/registry-deps-sonic-gnmi-20261118) and is not yet landed. This registration must remain Draft until the source prerequisite lands.

```starlark
bazel_dep(
    name = "sonic-gnmi",
    version = "0.1.1-678f15def7c4ca6946d2fb94918e3fe6cf47d982",
)
```

Current dependency versions are in [MODULE.bazel](MODULE.bazel). They select the published catalog at [`3d1cc5e8dfd5`](https://github.com/securely1g/sonic-bazel-registry/tree/3d1cc5e8dfd553d2acbe4198e504a245e6bdbddf).

The owner applies the existing Infrastructure policy that materializes the complete declared kernel tool tree for cached builds. This preserves caches and test assertions; the previous incomplete-tree failure still requires validation at this source revision.

## Presubmit contract

The retained registry matrix selects: `amd64`. Platform mappings, additional architecture-specific targets and consumer settings are defined in [presubmit.json](presubmit.json). These declarations describe coverage, not a claim that CI passed.

Build targets:

```text
//:consumer
@sonic-gnmi//dist:runtime
@sonic-gnmi//dist:runtime.debug_symbols
@sonic-gnmi//dist:runtime_packages.json
@sonic-gnmi//dist:sources
@sonic-gnmi//gnoi_yang:server
```

Test targets:

```text
@sonic-gnmi//dist:package_test
@sonic-gnmi//dist:source_test
@sonic-gnmi//dist:installed_runtime_test
```

The standalone consumer is [tests/consumer](tests/consumer).

Source archive integrity and the ordered patch/overlay inputs are recorded in [source.json](source.json). [Previous registration notes](https://github.com/securely1g/sonic-bazel-registry/blob/3d1cc5e8dfd553d2acbe4198e504a245e6bdbddf/modules/sonic-gnmi/0.1.0-3cc2cba22ba980128518aafe4ddae14aeebebb08/README.md) describe `0.1.0-3cc2cba22ba980128518aafe4ddae14aeebebb08` and are historical rather than instructions for this version.
