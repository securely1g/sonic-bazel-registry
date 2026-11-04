# Native AMD64 Linkmgrd for docker-mux

This entry registers [Linkmgrd PR #1](https://github.com/securely1g/sonic-linkmgrd/pull/1)
at `803c4b170de1ebdf38d638517fd1115368ec9a5c`. Its source owner builds the daemon and matching runtime/debug TARs
for [docker-mux integration #123](https://github.com/securely1g/sonic-buildimage/issues/123).
No DEB is generated or imported as a substitute for the project source.

The runtime installs `/usr/sbin/linkmgrd` and its existing compressed Debian
changelog. The debug TAR contains the matching Build-ID symbols with `0644`
permissions. Common and libnl remain separately owned dependencies; the MUX
config-engine parent supplies their runtime TARs. Boost 1.83 comes from the
existing pinned target APT set.

The ordinary external consumer has no source overrides. Native AMD64/Trixie CI
builds the daemon (including its core libraries), two TARs and package metadata,
runs all 189 original C++ test cases and source-contract checks, then validates installed
ELF dependencies, real CLI behavior and GDB symbol discovery. Source CI
separately checks no-op/edit/restore behavior and traced C++ CodeQL coverage.
The output checks list file-producing targets. `linkmgrd_core` groups its C++
libraries through `CcInfo` and has no standalone default file; the daemon and
original tests compile and link those libraries. Acceptance for this new
registration is pending.

The existing source MODULE patch sets the registered version and aligns the
shared dependencies: infrastructure `0.0.26-2a6fc39c55be05e849b0e3a2d1808a4a59f123a6`
from [registry #218](https://github.com/securely1g/sonic-bazel-registry/pull/218)
and Common `0.0.8-43598143ef4a46431eae0859915cd7d951dad1ed` from
[#199](https://github.com/securely1g/sonic-bazel-registry/pull/199). The separate
consumer uses the same infrastructure. Published libnl `3.7.0.sonic.7` is
preserved. Other published dependency declarations remain unchanged; Common's
minimum selects Distroless `.16` through normal module resolution.

The source archive and production code, all four build targets and all three
tests remain unchanged. There is one unpublished candidate. Keep Draft until
required source/registry prerequisites land, this registration targets maintained
main and current CI passes. Ordinary-consumer and MUX acceptance must be verified
on these exact inputs; earlier receipts retain their original dependency graph.
