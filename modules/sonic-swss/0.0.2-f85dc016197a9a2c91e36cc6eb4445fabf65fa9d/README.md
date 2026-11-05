# SWSS with the shared libteam owner

This entry registers [SWSS source f85dc016](https://github.com/securely1g/sonic-swss/commit/f85dc016197a9a2c91e36cc6eb4445fabf65fa9d), proposed in [source PR #10](https://github.com/securely1g/sonic-swss/pull/10). Its declared module base is `0.0.2`; the registry version appends that exact source commit. The only source patch changes this module identity. Program versions, SONAMEs and existing Make/DEB recipes are unchanged.

| Consumer input | Published `0.0.1-88d9cc2b...` | This entry |
| --- | --- | --- |
| `teamsyncd` libteam headers and libraries | Imported Debian libteam development package | Source-owned `@libteam//:libteam` and `:libteamdctl` providers |
| `tlm_teamd` dependency | Imported Debian libteam development package | Owner libteamdctl provider and the existing Jansson dependency |
| Runtime package records | Imported libteam package controls | Owner library-only metadata for `libteam5` and `libteamdctl0` |
| Library TAR handoff | No SWSS owner-TAR exports | `@sonic-swss//dist:libteam_runtime` and `:libteam_debug` export the two owner library TARs and matching debug TARs |

The library TARs remain separate from `@sonic-swss//dist:swss_pkg` and its debug TAR. An OCI consumer installs those matching outputs together. This registration does not add a libteam-utils package record to an image that installs only the libraries, and does not add a synthetic libteam dependency to `teammgrd`.

## Validation contract

`presubmit.json` retains both automatic AMD64 and ARM64 configurations, matching host/target platforms, all seven existing consumer dependency selections and Rust 1.90.0 with bindgen and mangled allocator libraries. It retains these five build targets:

- `@sonic-swss//dist:cpp_binaries`
- `@sonic-swss//dist:swss_pkg`
- `@sonic-swss//dist:swss_pkg.debug_symbols`
- `@sonic-swss//dist:runtime_packages.json`
- `@sonic-swss//crates/countersyncd:countersyncd`

It adds the two owner TAR export groups and retains all three tests: `gcovpreload_test`, `protobuf_runtime_test` and `common_rust_test`. These jobs build native targets and TAR outputs; they do not select a DEB producer or a full VS installer.

The reusable library's `@libteam//:consumer_test`, package/debug tests and incremental probe belong to [registry PR #236](https://github.com/securely1g/sonic-bazel-registry/pull/236). They are separate owner validation, not extra tests claimed by this SWSS presubmit. Source PR #10 owns the installed SWSS/libteam loader checks, including rejection of host-library fallback. Registry target success alone does not establish those installed checks or complete image integration.

## Dependencies and readiness

This candidate is stacked on the immutable #236 catalog `942ba547eeefba82f4649dedebb10762baba87dd`, which includes the shared CI transport from [PR #238](https://github.com/securely1g/sonic-bazel-registry/pull/238) and Unicode build-event repair from [PR #241](https://github.com/securely1g/sonic-bazel-registry/pull/241). Those prerequisites and the selected source revision remain unlanded. Normal consumer defaults remain on maintained registry `main`; an authorized Draft validation can temporarily replace its single SONiC registry endpoint with the complete candidate catalog.

Local preparation verifies the source archive, identity patch, published-entry preservation and presubmit scope. Native validation of this registration is pending. Retaining automatic ARM64 coverage does not claim ARM64 acceptance. The complete stack includes maintained main `c7c4e94ba937ee8ecf83f05c6fab40a349ad8c10`, preserving its published BMv2 and FIPS entries. The SWSS feature remains one separate commit above its reviewed owner prerequisite; shared runner and transport repairs remain in their own prerequisite commits. Keep this PR Draft until its source and prerequisites land and required native validation passes.
