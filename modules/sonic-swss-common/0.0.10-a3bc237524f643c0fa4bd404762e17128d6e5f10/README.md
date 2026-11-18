# sonic-swss-common

Registry version `0.0.10-a3bc237524f643c0fa4bd404762e17128d6e5f10` uses [the source snapshot](https://github.com/securely1g/sonic-swss-common/tree/a3bc237524f643c0fa4bd404762e17128d6e5f10) from `securely1g/sonic-swss-common`. The source repository owns its build definitions and dependency pins; this entry adds the commit-qualified module identity and retained registry integration.

The pinned source is preserved on [the owner branch](https://github.com/securely1g/sonic-swss-common/tree/codex/registry-deps-sonic-swss-common-20261118) and is not yet landed. This registration must remain Draft until the source prerequisite lands.

```starlark
bazel_dep(
    name = "sonic-swss-common",
    version = "0.0.10-a3bc237524f643c0fa4bd404762e17128d6e5f10",
)
```

Current dependency versions are in [MODULE.bazel](MODULE.bazel). They select the published catalog at [`3d1cc5e8dfd5`](https://github.com/securely1g/sonic-bazel-registry/tree/3d1cc5e8dfd553d2acbe4198e504a245e6bdbddf).

The source already contains the reviewed libyang runtime integration, so this new entry does not repeat the superseded registry patch. Its runtime regression coverage is retained.

## Presubmit contract

The retained registry matrix selects: `amd64`, `arm64`. Platform mappings, additional architecture-specific targets and consumer settings are defined in [presubmit.json](presubmit.json). These declarations describe coverage, not a claim that CI passed.

Build targets:

```text
@sonic-swss-common//common:cfg_schema_generated
@sonic-swss-common//:common
@sonic-swss-common//:libswsscommon_consolidated.so
@sonic-swss-common//:swssloglevel
@sonic-swss-common//dist:libswsscommon_pkg
@sonic-swss-common//dist:libswsscommon_pkg.debug_symbols
@sonic-swss-common//dist:sonic-db-cli_pkg
@sonic-swss-common//pyext:swsscommon_pkg
@sonic-swss-common//goext:swsscommon
@sonic-swss-common//crates/swss-common:swss_common
@sonic-swss-common//dist:sonic-db-cli_pkg.debug_symbols
@sonic-swss-common//pyext:swsscommon_pkg.debug_symbols
@sonic-swss-common//:runtime_packages.json
@sonic-swss-common//crates/swss-common:swss_common_async
@sonic-swss-common//crates/swss-common-testing:swss_common_testing
@sonic-swss-common//crates/swss-common-testing:swss_common_testing_async
```

Test targets:

```text
@sonic-swss-common//tests:status_code_util_test
@sonic-swss-common//tests:saiaclschema_ut
@sonic-swss-common//tests:notification_queue_ut
@sonic-swss-common//tests:interface_ut
@sonic-swss-common//tests:vrf_ut
@sonic-swss-common//tests:shared_library_runtime_test
@sonic-swss-common//tests:defaultvalueprovider_ut
@sonic-swss-common//dist:libswsscommon_package_test
@sonic-swss-common//pyext:swsscommon_package_test
@sonic-swss-common//goext:swsscommon_runtime_test
@sonic-swss-common//dist:package_timestamps_test
@sonic-swss-common//crates/swss-common:swss_common_test
@sonic-swss-common//tools/bazel/rust:shared_serde_test
@sonic-swss-common//sonic-db-cli:shared_library_test
@sonic-swss-common//tools/bazel/runtime:declared_loader_test
@sonic-swss-common//goext/tests/hiredis:hiredis_cgo_test
@sonic-swss-common//goext/tests/gnmi:alias_test
@sonic-swss-common//sonic-db-cli:declared_shared_library_test
@sonic-swss-common//tests:redis_lua_path_test
@sonic-swss-common//tests/shared_netlink:consumer_test
@sonic-swss-common//tests:shared_library_elf_test
@sonic-swss-common//crates/swss-common:swss_common_async_test
@sonic-swss-common//tools/bazel/rust:testing_interface_test
@sonic-swss-common//tools/bazel/rust:async_testing_interface_test
```

Source archive integrity and the ordered patch/overlay inputs are recorded in [source.json](source.json). [Previous registration notes](https://github.com/securely1g/sonic-bazel-registry/blob/3d1cc5e8dfd553d2acbe4198e504a245e6bdbddf/modules/sonic-swss-common/0.0.9-334389eae54afd1f4f5ee69f89c3a7ad2062ee61/README.md) describe `0.0.9-334389eae54afd1f4f5ee69f89c3a7ad2062ee61` and are historical rather than instructions for this version.
