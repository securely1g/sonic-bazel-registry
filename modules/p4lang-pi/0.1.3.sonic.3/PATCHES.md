# PI cross-configuration patch

`overlay/bazel/cross-configure.patch` applies to the unchanged checksum-pinned
PI 0.1.3 source archive through the `pi_source` repository rule.

It replaces the gtest source `AC_CHECK_FILE` call with `AS_IF([test -r ...])`.
The path is a vendored source file on the build machine, so this check remains
valid when the target CPU differs. The original missing-submodule error is
preserved. No generated probe results, target filesystem facts, library code,
or test selection are changed.

The companion Bazel overlay enables `configure_xcompile = True` on the existing
SDK build. This uses rules_foreign_cc's standard configure triplet support.
The original upstream and Debian archive URLs and SHA-256 digests are retained.
