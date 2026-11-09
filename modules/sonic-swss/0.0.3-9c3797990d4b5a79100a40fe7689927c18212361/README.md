# SWSS with the shared libteam owner

This entry registers [SWSS source ee5a197a](https://github.com/securely1g/sonic-swss/commit/ee5a197adb6ae19c891a8844017d590969a10e4c), the landed squash of [source PR #10](https://github.com/securely1g/sonic-swss/pull/10) on SWSS `master`. Its declared module base is `0.0.2`; the registry version appends that exact source commit. The only source patch changes this module identity. Program versions, SONAMEs and existing Make/DEB recipes are unchanged.

| Consumer input | Published `0.0.1-88d9cc2b...` | This entry |
| --- | --- | --- |
| `teamsyncd` libteam headers and libraries | Imported Debian libteam development package | Source-owned `@libteam//:libteam` and `:libteamdctl` providers |
| `tlm_teamd` dependency | Imported Debian libteam development package | Owner libteamdctl provider and the existing Jansson dependency |
| SWSS dependency metadata | Imported libteam package controls | `@libteam//:library_runtime_packages.json` resolves `libteam5` and `libteamdctl0`; SWSS still emits only its own package record |
| Library TAR handoff | No SWSS owner-TAR exports | `@sonic-swss//dist:libteam_runtime` and `:libteam_debug` export the two owner library TARs and matching debug TARs |

The owner package metadata remains a separate public target; the two TAR groups do not reexport metadata JSON. The library TARs remain separate from `@sonic-swss//dist:swss_pkg` and its debug TAR. An OCI consumer installs those matching outputs together. This registration does not add a libteam-utils package record to an image that installs only the libraries, and does not add a synthetic libteam dependency to `teammgrd`.

## Validation contract

`presubmit.json` retains both automatic AMD64 and ARM64 configurations, matching host/target platforms, all seven existing consumer dependency selections and Rust 1.90.0 with bindgen and mangled allocator libraries. It retains these five build targets:

- `@sonic-swss//dist:cpp_binaries`
- `@sonic-swss//dist:swss_pkg`
- `@sonic-swss//dist:swss_pkg.debug_symbols`
- `@sonic-swss//dist:runtime_packages.json`
- `@sonic-swss//crates/countersyncd:countersyncd`

It adds the two owner TAR export groups and retains all three tests: `gcovpreload_test`, `protobuf_runtime_test` and `common_rust_test`. These jobs build native targets and TAR outputs; they do not select a DEB producer or a full VS installer.

The reusable library's `@libteam//:consumer_test`, package/debug tests and incremental probe belong to [registry PR #236](https://github.com/securely1g/sonic-bazel-registry/pull/236). They are separate owner validation, not extra tests claimed by this SWSS presubmit. Source PR #10 owns the installed SWSS/libteam loader checks, including rejection of host-library fallback. Registry target success alone does not establish those installed checks or complete image integration.

## Dependencies

This entry consumes `libteam@1.31.0.sonic.1`, published on maintained registry `main` by [PR #236](https://github.com/securely1g/sonic-bazel-registry/pull/236). That catalog uses the [merged Debian mirror configuration](https://github.com/securely1g/sonic-bazel-registry/pull/269). Normal consumer defaults remain on maintained registry `main`; an authorized Draft validation can temporarily replace its single SONiC registry endpoint with the complete candidate catalog.

Local preparation verifies the source archive, identity patch, published-entry preservation and presubmit scope. The PR description records native validation for each candidate; retaining automatic ARM64 coverage alone does not claim ARM64 acceptance. Native validation remains required for merging, independently of Draft/Ready state.
