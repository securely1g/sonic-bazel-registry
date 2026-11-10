# PI source and native dependency adaptations

`overlay/bazel/cross-configure.patch` applies to the unchanged checksum-pinned
PI 0.1.3 source archive through the `pi_source` repository rule.

Both configure scripts check files shipped with the source tarball. The top-level
script checks the vendored gtest source, and the proto subdirectory checks
`p4/v1/p4runtime.proto`. Use `AS_IF([test -r ...])` so the checks run on
the build machine during native and cross configuration. Missing inputs still
produce the upstream submodule errors.

The companion Bazel overlay enables `configure_xcompile = True` on the existing
SDK build. This uses rules_foreign_cc's standard configure triplet support.
The original upstream and Debian archive URLs and SHA-256 digests are retained.

## Stable PI SDK installation paths

`overlay/bazel/pi.BUILD.bazel` carries the same stable-prefix and compiler-path
adjustment reviewed in [registry #291](https://github.com/securely1g/sonic-bazel-registry/pull/291)
and [registry #296](https://github.com/securely1g/sonic-bazel-registry/pull/296).
The implementation is preserved from
[commit 0978962](https://github.com/securely1g/sonic-bazel-registry/blob/097896297e0a87ebe54a81426d223ec8cc9c8f5d/modules/p4lang-pi/0.1.3.sonic.4/overlay/bazel/pi.BUILD.bazel).
Both earlier proposals carried the same stable-prefix implementation. The
existing unpublished `.sonic.5` proposal preserves that change and leaves
published `.sonic.4` unchanged.

The adaptation is maintained in the registry overlay, not as an upstream PI
source patch. Existing `configure_make` settings provide a logical `/usr`
prefix, `DESTDIR` staging, and compiler file-prefix mapping. The installed SDK
layout is preserved. That stable-prefix adjustment adds no package producer.
The separate native-core changes below patch owned source and explicitly declare
the existing FE binary as an SDK provider output.

The existing .5 native AMD64/ARM64 presubmit selects `:runtime`,
`:runtime.debug_symbols`, `:sdk`, and `:runtime_packages.json`, then runs
`:runtime_test`. The cross-configuration patch above and all existing consumer
checks are retained.


## Native core validation in the .5 update

The two BUILD overlays retain upstream target source globs, disabled internal-RPC
exclusions and the existing local source importer. The new native targets are
additive; SDK/runtime rules and their prefix/DESTDIR handling remain unchanged.
The copied upstream comment about lacking Bazel CI is replaced with the actual
AMD64 presubmit scope; action-query collection is separate. The native-only
public-header adaptation is described below.
Original fixture files are referenced from the pinned source repository rather
than rewritten or copied into a new packaging layer.

The SDK explicitly declares the existing installed `bin/pi_gen_fe_defines` as
an `out_data_files` result for the comparison test's existing `installed_file`
selection. The three runtime `_PROGRAMS`, configure/install commands, twelve
shared libraries and Python payload remain unchanged. This exposes an original
installed file; it does not generate or package a new program.

- The public cJSON target preserves the original `LIBADD = -lm` in the native library
  dependency graph, including both native generator targets.

## Public cJSON include selection for the native core

The same `cross-configure.patch` retains its original configure hunks and adds
only an include conditional in the ten owned PI config-reader/P4Info C files.
`PI_NATIVE_PUBLIC_CJSON` selects the public module's `<cJSON.h>`; its undefined
branch retains the original Make/SDK `<cJSON/cJSON.h>` include. Only
`native_pip4info` sets this compiler definition. No cJSON or uthash source is
patched, and no private build-rule replacement is added.

The BCR cJSON version is newer than PI's vendored copy. Compatibility is checked
by the original old/new generator fixtures and the existing SDK/runtime tests;
a passing build or ABI result has not yet been claimed. The public uthash
version matches the original vendored 2.3.0 API. The .5 update adds native
migration targets only for AMD64, while retaining the existing ARM SDK/runtime
and global compatibility checks. Published module entries stay unchanged.

The owned src/p4info/p4info.c deallocator selects cJSON_free only under PI_NATIVE_PUBLIC_CJSON. The legacy branch retains cJSON_Delete_char. This adapts one owned API call to the verified public header, without a replacement dependency rule or public-source patch.
