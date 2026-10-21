# Distroless headers and real Debian installation

Buildimage #33 consumes source-built P4/DASH TARs from its #13 base and also
installs locked Debian dependencies with real APT configuration and triggers.
It needs both the header fixes in registry #96 and `apt_install` in registry #72.

This candidate composes `.sonic.10` with the unchanged installer implementation from
`.sonic.8`; only the MODULE hunk context includes the existing foreign-build
dependency. No prior entry changes. The installer adds original archive labels
and configured filesystem TARs; runtime TARs never fabricate dpkg package records.

The native AMD64/ARM64 presubmit keeps all 20 `.sonic.10` tests and adds the
installer unit test and original-DEB identity test. These tests import existing
Debian archives and create no DEB packages. Full native registry validation and
actual PR33 installed-image validation remain required.

Direct prerequisites: https://github.com/securely1g/sonic-bazel-registry/pull/96
and https://github.com/securely1g/sonic-bazel-registry/pull/72. This single-module
proposal is stacked on #96; retarget maintained main after both land.
