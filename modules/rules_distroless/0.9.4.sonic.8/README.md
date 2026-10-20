# Debian installation with retained pkg-config fixes

This version retains every `0.9.4.sonic.6` fix and accepts pkg-config fields
with tabs, spaces or no whitespace after `:`. It distinguishes fields from
variables using the first `:` or `=`, so URLs in variables and `-DNAME=value`
compiler flags remain intact. Keys and values lose boundary whitespace.

Debian `libxtables-dev` 1.8.11-2 uses colon-tabs in `xtables.pc`. Previously,
its imported C/C++ target declared the headers but lost its include directory
and linker metadata. The native [iproute2 migration in PR #64](https://github.com/securely1g/sonic-bazel-registry/pull/64)
exposed the missing include root when compiling `tc/em_ipset.c`.

[Patch provenance and validation](PATCHES.md) describes the retained fixes
and fourteen native AMD64/ARM64 regression and integration tests. CI uses Bazel
8.5.1. The new header fixture imports checksum-pinned Debian xtables packages,
then compiles against the development import's actual compilation context.
It omits runtime linker inputs and does not claim xtables runtime coverage.
The tests do not produce DEB packages.

## Original Debian package installation

This candidate retains every published `0.9.4.sonic.7` patch, including the
pkg-config field separator fix and its native xtables tests. It adds the
optional `apt_install` backport from [rules_distroless #2](https://github.com/securely1g/rules_distroless/pull/2),
commit `b3d0573b06b682a7ae3d5de20cc8215b3be3a037`. The rule configures
original checksum-verified DEBs using real APT/dpkg, package scripts and
triggers in an isolated filesystem. The configured filesystem TAR replaces
the preceding filesystem; appending it could restore removed files.

Registry tests cover the installer unit contract and unchanged original DEB
exports, alongside every retained native regression. They import existing
DEBs and do not produce new packages. Full native installation lifecycle tests
remain owned by source PR #2; registry tests do not establish full-image proof.

[Buildimage #33](https://github.com/securely1g/sonic-buildimage/pull/33) consumes
the earlier installer snapshot through its explicit draft-source manifest.
Its owner must update the declared version and manifest to this candidate and
validate the resulting image separately. Published `.sonic.7` stays unchanged.
