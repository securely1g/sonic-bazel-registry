# sonic-dash

Registry version `0.0.4-42d274f1ba5aa8f248ef4bb9f2fce9e0a0738164` uses [the source snapshot](https://github.com/securely1g/DASH/tree/42d274f1ba5aa8f248ef4bb9f2fce9e0a0738164) from `securely1g/DASH`. The source repository owns its build definitions and dependency pins; this entry adds the commit-qualified module identity and retained registry integration.

The pinned source is preserved on [the owner branch](https://github.com/securely1g/DASH/tree/codex/registry-deps-sonic-dash-20261118) and is not yet landed. This registration must remain Draft until the source prerequisite lands.

```starlark
bazel_dep(
    name = "sonic-dash",
    version = "0.0.4-42d274f1ba5aa8f248ef4bb9f2fce9e0a0738164",
)
```

Current dependency versions are in [MODULE.bazel](MODULE.bazel). They select the published catalog at [`3d1cc5e8dfd5`](https://github.com/securely1g/sonic-bazel-registry/tree/3d1cc5e8dfd553d2acbe4198e504a245e6bdbddf).

## Presubmit contract

The retained registry matrix selects: `amd64`, `arm64`. Platform mappings, additional architecture-specific targets and consumer settings are defined in [presubmit.json](presubmit.json). These declarations describe coverage, not a claim that CI passed.

Build targets:

```text
@sonic-dash//:runtime
@sonic-dash//:runtime.debug_symbols
@sonic-dash//:sdk
@sonic-dash//:runtime_packages.json
```

Test targets:

```text
@sonic-dash//bazel:runtime_test
@sonic-dash//bazel:make_flags_test
```

Source archive integrity and the ordered patch/overlay inputs are recorded in [source.json](source.json). [Previous registration notes](https://github.com/securely1g/sonic-bazel-registry/blob/3d1cc5e8dfd553d2acbe4198e504a245e6bdbddf/modules/sonic-dash/0.0.3-2cbfdfa1205c0d03003444e5c80f89adb8c3df59/README.md) describe `0.0.3-2cbfdfa1205c0d03003444e5c80f89adb8c3df59` and are historical rather than instructions for this version.
