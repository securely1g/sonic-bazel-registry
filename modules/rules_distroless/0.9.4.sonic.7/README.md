# pkg-config field separators

This version retains every `0.9.4.sonic.6` fix and accepts pkg-config fields
with tabs, spaces or no whitespace after `:`. It distinguishes fields from
variables using the first `:` or `=`, so URLs in variables and `-DNAME=value`
compiler flags remain intact. Keys and values lose boundary whitespace.

Debian `libxtables-dev` 1.8.11-2 uses colon-tabs in `xtables.pc`. Previously,
its imported C/C++ target declared the headers but lost its include directory
and linker metadata. The native [iproute2 migration in PR #64](https://github.com/securely1g/sonic-bazel-registry/pull/64)
exposed the missing include root when compiling `tc/em_ipset.c`.

[Patch provenance and validation](PATCHES.md) describes the retained fixes
and twelve native AMD64/ARM64 regression and integration tests. CI uses Bazel
8.5.1. The new header fixture imports checksum-pinned Debian xtables packages,
then compiles against the development import's actual compilation context.
It omits runtime linker inputs and does not claim xtables runtime coverage.
The tests do not produce DEB packages.
