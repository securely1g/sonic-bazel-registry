# sonic-dash-api

Registry version `0.0.6-55310bf7437d67411418c974587adcdc1b194d6b` uses [the source snapshot](https://github.com/securely1g/sonic-dash-api/tree/55310bf7437d67411418c974587adcdc1b194d6b) from `securely1g/sonic-dash-api`. The source repository owns its build definitions and dependency pins; this entry adds the commit-qualified module identity and retained registry integration.

This exact source commit landed through [the owner change](https://github.com/securely1g/sonic-dash-api/pull/10). Registry build/test acceptance is separate from source provenance.

```starlark
bazel_dep(
    name = "sonic-dash-api",
    version = "0.0.6-55310bf7437d67411418c974587adcdc1b194d6b",
)
```

Current dependency versions are in [MODULE.bazel](MODULE.bazel). They select the published catalog at [`3d1cc5e8dfd5`](https://github.com/securely1g/sonic-bazel-registry/tree/3d1cc5e8dfd553d2acbe4198e504a245e6bdbddf).

## Presubmit contract

The retained registry matrix selects: `amd64`, `arm64`. Platform mappings, additional architecture-specific targets and consumer settings are defined in [presubmit.json](presubmit.json). These declarations describe coverage, not a claim that CI passed.

Build targets:

```text
@sonic-dash-api//:libdashapi_pkg
@sonic-dash-api//:libdashapi_pkg.debug_symbols
@sonic-dash-api//:protobuf_runtime_pkg
@sonic-dash-api//:protobuf_debug_pkg
@sonic-dash-api//bazel:runtime_consumer_test
@sonic-dash-api//:runtime_packages.json
@sonic-dash-api//:ha_schema_sources
@sonic-dash-api//bazel:ha_schema_descriptor
```

Test targets:

```text
@sonic-dash-api//bazel:source_contract_test
@sonic-dash-api//bazel:runtime_consumer_test
@sonic-dash-api//bazel:utils_test
@sonic-dash-api//misc:python_test
@sonic-dash-api//bazel:ha_schema_test
```

Source archive integrity and the ordered patch/overlay inputs are recorded in [source.json](source.json). [Previous registration notes](https://github.com/securely1g/sonic-bazel-registry/blob/3d1cc5e8dfd553d2acbe4198e504a245e6bdbddf/modules/sonic-dash-api/0.0.5-9b2893e890734a2db0c53a5e5c64b031ec0dcfbd/README.md) describe `0.0.5-9b2893e890734a2db0c53a5e5c64b031ec0dcfbd` and are historical rather than instructions for this version.
