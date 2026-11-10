# Native AMD64 Linkmgrd for docker-mux

This entry registers [Linkmgrd PR #1](https://github.com/securely1g/sonic-linkmgrd/pull/1)
at `78c59dae0802dcbbe43c943a626189b36aac9a24`. Its source owner builds the daemon and matching runtime/debug TARs
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

The registration patch sets only the source module version. The producer
and independent consumer use the maintained infrastructure 0.0.28.
Linkmgrd consumes Common 0.0.9 and the libnl 3.7.0.sonic.7 shared
interfaces through their declared CcInfo providers. Its installed-package
tests require all three expected native SONAMEs. The root selects the
reviewed build-infra Trixie APT lock and Distroless 0.9.4.sonic.18.
The native source and the registry consumer each exercise the exported
TARs. Image-level validation belongs to buildimage #147.
