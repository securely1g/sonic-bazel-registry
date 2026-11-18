# sonic-build-infra

Registry version `0.0.39-7c1452148a48adf5095952144456b98044cd9914` uses [the source snapshot](https://github.com/securely1g/sonic-build-infra/tree/7c1452148a48adf5095952144456b98044cd9914) from `securely1g/sonic-build-infra`. The source repository owns its build definitions and dependency pins; this entry adds the commit-qualified module identity and retained registry integration.

The pinned source is preserved on [the owner branch](https://github.com/securely1g/sonic-build-infra/tree/codex/registry-deps-sonic-build-infra-20261118) and is not yet landed. This registration must remain Draft until the source prerequisite lands.

```starlark
bazel_dep(
    name = "sonic-build-infra",
    version = "0.0.39-7c1452148a48adf5095952144456b98044cd9914",
)
```

Current dependency versions are in [MODULE.bazel](MODULE.bazel). They select the published catalog at [`3d1cc5e8dfd5`](https://github.com/securely1g/sonic-bazel-registry/tree/3d1cc5e8dfd553d2acbe4198e504a245e6bdbddf).

## Presubmit contract

The retained registry matrix selects: `amd64`, `arm64`. Platform mappings, additional architecture-specific targets and consumer settings are defined in [presubmit.json](presubmit.json). These declarations describe coverage, not a claim that CI passed.

Build targets:

```text
@sonic-build-infra//tools/build_tools:make
@sonic-build-infra//tools/build_tools:m4
@sonic-build-infra//tools/build_tools:pkgconf
@sonic-build-infra//tools/build_tools:perl
@sonic-build-infra//tools/build_tools:bison
@sonic-build-infra//tools/build_tools:flex
@sonic-build-infra//tools/build_tools:autoconf
@sonic-build-infra//tools/build_tools:autoheader
@sonic-build-infra//tools/build_tools:autom4te
@sonic-build-infra//tools/build_tools:launcher_action_check
@sonic-build-infra//tools/build_tools:configure_probe_binary
@sonic-build-infra//tools/build_tools:compile_et
@sonic-build-infra//tools/build_tools:mk_cmds
@sonic-build-infra//tests:hello_cpp
@sonic-build-infra//tests:hello_deploy_tar
@sonic-build-infra//tests:hello_deploy_tar.debug_symbols
@sonic-build-infra//tests:libgreet.so
@sonic-build-infra//tools/build_tools:foreign_runtime
@sonic-build-infra//tools/build_tools:metadata_runtime
@sonic-build-infra//tools/build_tools:autoreconf
@sonic-build-infra//tools/build_tools:automake
@sonic-build-infra//tools/build_tools:aclocal
@sonic-build-infra//tools/build_tools:libtoolize
@sonic-build-infra//tools/build_tools:protoc
@sonic-build-infra//tools/build_tools:grpc_cpp_plugin
@sonic-build-infra//tools/build_tools:grpc_python_plugin
@sonic-build-infra//tools/build_tools:thrift
@sonic-build-infra//tools/build_tools:python3
@sonic-build-infra//registry_ci:kernel_runtime_manifest
@sonic-build-infra//deps/compiler:alternatives_pkg
@sonic-build-infra//deps/automake:alternatives_pkg
@sonic-build-infra//deps/openmpi:alternatives_pkg
@sonic-build-infra//tools/build_tools:patch
@sonic-build-infra//tools/build_tools:xmllint
@sonic-build-infra//tools/build_tools:xsltproc
@sonic-build-infra//tools/build_tools:libtool_program
@sonic-build-infra//tools/build_tools:libtool_library
@sonic-build-infra//tools/build_tools:libtool_c_library
@sonic-build-infra//tools/build_tools:libtool_config
@sonic-build-infra//tools/build_tools:libtool_argv_validation
@sonic-build-infra//binary/tests:strip_static_archive_check
```

Test targets:

```text
@sonic-build-infra//tools/build_tools:runtime_test
@sonic-build-infra//tools/build_tools:configure_runtime_test
@sonic-build-infra//tools/build_tools:configure_make_test
@sonic-build-infra//toolchains/gcc/tests:foreign_link_test
@sonic-build-infra//tools/build_tools:kerberos_runtime_test
@sonic-build-infra//tests:hello_strip_test
@sonic-build-infra//tests:libgreet_pic_test
@sonic-build-infra//tests:libgreet_strip_test
@sonic-build-infra//tests:hello_deploy_tar_content_test
@sonic-build-infra//tests:hello_deploy_tar_provides_debug_symbols_test
@sonic-build-infra//cc/tests:transitive_runtime_test
@sonic-build-infra//cc/tests:shared_library_layout_test
@sonic-build-infra//tools/build_tools:foreign_runtime_test
@sonic-build-infra//tools/build_tools:libtool_test
@sonic-build-infra//oci/tests:account_layer_test
@sonic-build-infra//oci/tests:installed_packages_test
@sonic-build-infra//oci/tests:owner_metadata_test
@sonic-build-infra//oci/tests:installed_packages_rule_test
@sonic-build-infra//oci/tests:runtime_packages_test
@sonic-build-infra//oci/tests:runtime_packages_rule_test
@sonic-build-infra//tools/build_tools:prepare_rootfs_test
@sonic-build-infra//tools/build_tools:kernel_debian_test
@sonic-build-infra//tools/build_tools:runtime_launcher_test
@sonic-build-infra//deps:alternatives_test
@sonic-build-infra//tools/build_tools:kernel_runtime_tools_test
@sonic-build-infra//testing:exec_test_args_test
@sonic-build-infra//cc/tests/runtime_context:layout_test
@sonic-build-infra//cc/tests/runtime_test:preparation_test
@sonic-build-infra//cc/tests/runtime_test:contract_test
@sonic-build-infra//cc/tests/runtime_test:native_test
@sonic-build-infra//cc/tests/runtime_test:origin_contract_test
@sonic-build-infra//tar:root_owned_tar_test
@sonic-build-infra//tar:debug_symbols_ownership_test
@sonic-build-infra//tests:installation_rpath_tar_test
@sonic-build-infra//tests:hello_rpath_installation_test
@sonic-build-infra//tests:hello_runpath_installation_test
@sonic-build-infra//registry_ci:prefix_map_test
@sonic-build-infra//tools/build_tools:perl_bookworm_test
@sonic-build-infra//tools/build_tools:bookworm_test_runtime_test
@sonic-build-infra//tar:debug_symbols_modes_test
@sonic-build-infra//tests:deploy_tar_timestamps_test
@sonic-build-infra//oci/tests:installed_packages_alias_test
@sonic-build-infra//cc/tests/runtime_context:paired_layout_test
@sonic-build-infra//cc/tests/runtime_context:paired_flags_test
@sonic-build-infra//apt:lock_test
@sonic-build-infra//apt:bookworm_lock_test
@sonic-build-infra//binary/tests:strip_static_archive_test
@sonic-build-infra//binary/tests:stripped_archive_consumer_test
```

Additional `amd64` build targets:

```text
@sonic-build-infra//tools/build_tools:docbook_runtime
@sonic-build-infra//tools/build_tools:docbook2man
```

Additional `amd64` test targets:

```text
@sonic-build-infra//registry_ci:kernel_arm64_tools_test
@sonic-build-infra//registry_ci:kernel_armhf_tools_test
@sonic-build-infra//tools/build_tools:docbook_runtime_test
```

Source archive integrity and the ordered patch/overlay inputs are recorded in [source.json](source.json). [Previous registration notes](https://github.com/securely1g/sonic-bazel-registry/blob/3d1cc5e8dfd553d2acbe4198e504a245e6bdbddf/modules/sonic-build-infra/0.0.38-0baa4acc9eac9ccc793b81104b1580d530271cbe/README.md) describe `0.0.38-0baa4acc9eac9ccc793b81104b1580d530271cbe` and are historical rather than instructions for this version.
