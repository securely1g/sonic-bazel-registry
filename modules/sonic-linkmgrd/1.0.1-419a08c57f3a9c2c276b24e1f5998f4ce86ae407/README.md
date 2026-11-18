## Registry dependency refresh: `1.0.1-419a08c57f3a9c2c276b24e1f5998f4ce86ae407`

Source: `securely1g/sonic-linkmgrd@419a08c57f3a9c2c276b24e1f5998f4ce86ae407`, based on `92c78b468b678e3c2ed2877d2cb0a52306f2297f`. Dependency targets are frozen to published registry snapshot `3d1cc5e8dfd553d2acbe4198e504a245e6bdbddf`. The source owns the module base version and dependency updates. The registry supplies the full commit-qualified identity and retains its existing integration behavior.

Full archive patch-application and build validation must be recorded separately.

# Native AMD64 Linkmgrd for docker-mux

This entry builds Linkmgrd from merged master commit `92c78b468b678e3c2ed2877d2cb0a52306f2297f`.
The active/standby test follows a port with its link down through active and
auto mode. For each input it uses the existing fixture, then dispatches
callbacks until the composite state changes and checks the expected state.
Only the scheduled probe waits for a future callback. The test checks that
the probe runs once and the two hardware writes request active, then standby.
It also checks that acknowledging standby leaves the write count at two.
[Active/standby test](https://github.com/securely1g/sonic-linkmgrd/blob/92c78b468b678e3c2ed2877d2cb0a52306f2297f/test/LinkManagerStateMachineTest.cpp#L610-L668)

The active/active recovery tests wait for the periodic probe and check that
exactly one corrective write restores the configured state in each direction.
[Linkmgrd #2](https://github.com/securely1g/sonic-linkmgrd/pull/2)

The daemon and its runtime and debug TARs are built from the same source.
[Original Bazel targets](https://github.com/securely1g/sonic-linkmgrd/pull/1) ·
[docker-mux integration](https://github.com/securely1g/sonic-buildimage/issues/123)

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
original tests compile and link those libraries.

The registration patch sets only the source module version. The producer
and independent consumer use the maintained infrastructure 0.0.37.
Linkmgrd consumes Common 0.0.9 and the libnl 3.7.0.sonic.7 shared
interfaces through their declared CcInfo providers. Its installed-package
tests require all three expected native SONAMEs. The root selects the
reviewed build-infra Trixie APT lock and Distroless 0.9.4.sonic.20.
The native source and the registry consumer each exercise the exported
TARs. Image-level validation belongs to buildimage #147.
