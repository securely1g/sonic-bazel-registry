# sonic-sairedis

Registry version `0.0.6-f710c09deb31a5edcd579312f53bf512c5122567` uses [the source snapshot](https://github.com/securely1g/sonic-sairedis/tree/f710c09deb31a5edcd579312f53bf512c5122567) from `securely1g/sonic-sairedis`. The source repository owns its build definitions and dependency pins; this entry adds the commit-qualified module identity and retained registry integration.

The pinned source is preserved on [the owner branch](https://github.com/securely1g/sonic-sairedis/tree/codex/registry-deps-sonic-sairedis-20261118) and is not yet landed. This registration must remain Draft until the source prerequisite lands.

```starlark
bazel_dep(
    name = "sonic-sairedis",
    version = "0.0.6-f710c09deb31a5edcd579312f53bf512c5122567",
)
```

Current dependency versions are in [MODULE.bazel](MODULE.bazel). They select the published catalog at [`3d1cc5e8dfd5`](https://github.com/securely1g/sonic-bazel-registry/tree/3d1cc5e8dfd553d2acbe4198e504a245e6bdbddf).

The registration retains its explicit reproducible gzip toolchain selection and existing runtime/debug package checks.

## Presubmit contract

The retained registry matrix selects: `amd64`, `arm64`. Platform mappings, additional architecture-specific targets and consumer settings are defined in [presubmit.json](presubmit.json). These declarations describe coverage, not a claim that CI passed.

Build targets:

```text
@sonic-sairedis//:canonical_outputs
@sonic-sairedis//lib:libsairedis_pkg
@sonic-sairedis//lib:libsairedis_pkg.debug_symbols
@sonic-sairedis//lib:libsairedis_dev_pkg
@sonic-sairedis//lib:libsairedis_dev_pkg.debug_symbols
@sonic-sairedis//meta:libsaimetadata_pkg
@sonic-sairedis//meta:libsaimetadata_pkg.debug_symbols
@sonic-sairedis//meta:libsaimetadata_dev_pkg
@sonic-sairedis//meta:libsaimetadata_dev_pkg.debug_symbols
@sonic-sairedis//vslib:libsaivs_pkg
@sonic-sairedis//vslib:libsaivs_pkg.debug_symbols
@sonic-sairedis//vslib:libsaivs_dev_pkg
@sonic-sairedis//vslib:libsaivs_dev_pkg.debug_symbols
@sonic-sairedis//syncd:syncd_pkg
@sonic-sairedis//syncd:syncd_pkg.debug_symbols
@sonic-sairedis//pyext:pysairedis_pkg
@sonic-sairedis//pyext:pysairedis_pkg.debug_symbols
@sonic-sairedis//:runtime_packages.json
@sonic-sairedis//:library_runtime_packages.json
```

Test targets:

```text
@sonic-sairedis//lib:tests_test
@sonic-sairedis//tests:tests_test
@sonic-sairedis//saiasiccmp:tests
@sonic-sairedis//unittest/meta:tests
@sonic-sairedis//unittest/proxylib:tests
@sonic-sairedis//unittest/saidump:tests
@sonic-sairedis//unittest/saisdkdump:tests
```

Source archive integrity and the ordered patch/overlay inputs are recorded in [source.json](source.json). [Previous registration notes](https://github.com/securely1g/sonic-bazel-registry/blob/3d1cc5e8dfd553d2acbe4198e504a245e6bdbddf/modules/sonic-sairedis/0.0.5-33443ea1666a23812365d03fb959066ee84c9aa0/README.md) describe `0.0.5-33443ea1666a23812365d03fb959066ee84c9aa0` and are historical rather than instructions for this version.
