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
