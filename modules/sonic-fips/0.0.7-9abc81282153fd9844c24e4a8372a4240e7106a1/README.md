# sonic-fips

Registry version `0.0.7-9abc81282153fd9844c24e4a8372a4240e7106a1` uses [the source snapshot](https://github.com/securely1g/sonic-fips/tree/9abc81282153fd9844c24e4a8372a4240e7106a1) from `securely1g/sonic-fips`. The source repository owns its build definitions and dependency pins; this entry adds the commit-qualified module identity and retained registry integration.

The pinned source is preserved on [the owner branch](https://github.com/securely1g/sonic-fips/tree/codex/registry-deps-sonic-fips-20261118) and is not yet landed. This registration must remain Draft until the source prerequisite lands.

```starlark
bazel_dep(
    name = "sonic-fips",
    version = "0.0.7-9abc81282153fd9844c24e4a8372a4240e7106a1",
)
```

Current dependency versions are in [MODULE.bazel](MODULE.bazel). They select the published catalog at [`3d1cc5e8dfd5`](https://github.com/securely1g/sonic-bazel-registry/tree/3d1cc5e8dfd553d2acbe4198e504a245e6bdbddf).

## Presubmit contract

The retained registry matrix selects: `amd64`, `arm64`. Platform mappings, additional architecture-specific targets and consumer settings are defined in [presubmit.json](presubmit.json). These declarations describe coverage, not a claim that CI passed.

Build targets:

```text
@sonic-fips//openssl:libssl3t64_pkg
@sonic-fips//openssl:openssl_pkg
@sonic-fips//openssl:libssl3t64_pkg.debug_symbols
@sonic-fips//openssl:openssl_pkg.debug_symbols
@sonic-fips//openssl:libssl_dev_pkg
@sonic-fips//openssh:openssh_client_pkg
@sonic-fips//openssh:openssh_client_pkg.debug_symbols
@sonic-fips//krb5:libk5crypto3_pkg
@sonic-fips//krb5:libk5crypto3_pkg.debug_symbols
@sonic-fips//krb5:libkrb5support0_pkg
@sonic-fips//krb5:libkrb5support0_pkg.debug_symbols
@sonic-fips//krb5:libkrb5_3_pkg
@sonic-fips//krb5:libkrb5_3_pkg.debug_symbols
@sonic-fips//krb5:libgssapi_krb5_2_pkg
@sonic-fips//krb5:libgssapi_krb5_2_pkg.debug_symbols
@sonic-fips//symcrypt:runtime
@sonic-fips//symcrypt:runtime.debug_symbols
@sonic-fips//:runtime_packages.json
```

Test targets:

```text
@sonic-fips//openssl:package_test
@sonic-fips//openssh:package_test
@sonic-fips//krb5:package_test
@sonic-fips//symcrypt:package_test
@sonic-fips//symcrypt:timestamp_test
@sonic-fips//openssl/integration:openssl_symcrypt_test
```

Source archive integrity and the ordered patch/overlay inputs are recorded in [source.json](source.json). [Previous registration notes](https://github.com/securely1g/sonic-bazel-registry/blob/3d1cc5e8dfd553d2acbe4198e504a245e6bdbddf/modules/sonic-fips/0.0.6-18a778db501d455f8a1b6d1e3ef8e17121661177/README.md) describe `0.0.6-18a778db501d455f8a1b6d1e3ef8e17121661177` and are historical rather than instructions for this version.
