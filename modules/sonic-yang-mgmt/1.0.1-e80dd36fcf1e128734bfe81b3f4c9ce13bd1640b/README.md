# sonic-yang-mgmt

Registry version `1.0.1-e80dd36fcf1e128734bfe81b3f4c9ce13bd1640b` uses [the source snapshot](https://github.com/securely1g/sonic-buildimage/tree/e80dd36fcf1e128734bfe81b3f4c9ce13bd1640b) from `securely1g/sonic-buildimage`. The source repository owns its build definitions and dependency pins; this entry adds the commit-qualified module identity and retained registry integration.

The pinned source is preserved on [the owner branch](https://github.com/securely1g/sonic-buildimage/tree/codex/registry-deps-sonic-yang-mgmt-20261118) and is not yet landed. This registration must remain Draft until the source prerequisite lands.

```starlark
bazel_dep(
    name = "sonic-yang-mgmt",
    version = "1.0.1-e80dd36fcf1e128734bfe81b3f4c9ce13bd1640b",
)
```

Current dependency versions are in [MODULE.bazel](MODULE.bazel). They select the published catalog at [`3d1cc5e8dfd5`](https://github.com/securely1g/sonic-bazel-registry/tree/3d1cc5e8dfd553d2acbe4198e504a245e6bdbddf), except for the YANG Models runtime-provider prerequisite below.

This source owns the Python library, source and runtime-test targets, wheel and installation TAR targets. It uses the Models runtime provider from `sonic-yang-models@1.0.2-1dbe7ad4ab7efab414537236eb2f8522ce1f8abd`; that source must also land before this registration is ready. The config-engine requirements lock remains checksum-pinned, and the public requirements-lock label remains an owner alias. This new entry removes superseded registry build overlays; previously published entries are unchanged.

## Presubmit contract

The retained registry matrix selects: `amd64`, `arm64`. Platform mappings, additional architecture-specific targets and consumer settings are defined in [presubmit.json](presubmit.json). These declarations describe coverage, not a claim that CI passed.

Build targets:

```text
@sonic-yang-mgmt//:sonic_yang_mgmt_sources
@sonic-yang-mgmt//:sonic_yang_mgmt_runtime_test
@sonic-yang-mgmt//:sonic_yang_mgmt_wheel
@sonic-yang-mgmt//:sonic-yang-mgmt.runtime
@sonic-yang-mgmt//:requirements_lock.txt
```

Test targets:

```text
@sonic-yang-mgmt//:sonic_yang_mgmt_runtime_test
```

Source archive integrity and the ordered patch/overlay inputs are recorded in [source.json](source.json). [Previous registration notes](https://github.com/securely1g/sonic-bazel-registry/blob/3d1cc5e8dfd553d2acbe4198e504a245e6bdbddf/modules/sonic-yang-mgmt/1.0.0-9ab452d22773c41783092ae3bd6c206d6c257c8d/README.md) describe `1.0.0-9ab452d22773c41783092ae3bd6c206d6c257c8d` and are historical rather than instructions for this version.
