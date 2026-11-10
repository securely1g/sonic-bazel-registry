# PI cross-configuration patch

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
Both proposals have the same build inputs; this new version leaves published
`.sonic.4` unchanged.

The adaptation is maintained in the registry overlay, not as an upstream PI
source patch. Existing `configure_make` settings provide a logical `/usr`
prefix, `DESTDIR` staging, and compiler file-prefix mapping. The installed SDK
layout and declared outputs stay unchanged. No source-archive patch, additional
build helper, or package producer is introduced.

The inherited native AMD64/ARM64 presubmit still builds `:runtime`,
`:runtime.debug_symbols`, `:sdk`, and `:runtime_packages.json`, then runs
`:runtime_test`. The cross-configuration patch above and all existing consumer
checks are retained.
