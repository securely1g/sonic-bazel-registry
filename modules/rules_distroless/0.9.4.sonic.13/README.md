# Lock import and real Debian installation

Buildimage #33 builds on #13's reviewed APT lock imports and installs those
original Debian archives with APT/dpkg. Version 0.9.4.sonic.13 composes registry
#111's lock-import support with #110's installer. It preserves both features,
including independent import namespaces, rather than reverting either parent.

The installer implementation is unchanged. Original-DEB aliases retain each
lock import's repository prefix and work in its payload-only path. Native
AMD64/ARM64 tests verify the original archive digest through two independent
imports, alongside all existing lock/header tests and installer unit tests.
They import existing Debian archives and do not create DEB packages. Actual
installed-image validation remains the consumer's responsibility.

Direct prerequisites: https://github.com/securely1g/sonic-bazel-registry/pull/110
and https://github.com/securely1g/sonic-bazel-registry/pull/111. This single-module
proposal is stacked on #111. Consumer:
https://github.com/securely1g/sonic-buildimage/pull/33.
