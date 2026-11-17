# libnl3 generated Debian controls

Version `3.7.0.sonic.8` retains the published `.7` native libraries, SONAMEs,
installation TARs, development SDK and matching debug outputs. It adds the
original Debian `dh_makeshlibs` / `dh_installdeb` control effects and reference
symbol inputs, using SONiC's explicit `DPKG_GENSYMBOLS_CHECK_LEVEL=0`.
The five runtime packages publish their real shlibs, symbols and ldconfig
triggers through the existing runtime-package metadata provider. The two
mapped development packages also publish their generated control files.

The new control test projects the authoritative generated control trees through
the shared infrastructure interface and checks the original package version,
resolved fields, SONAME metadata and Debhelper ldconfig triggers. Existing raw
shared consumers, installed SDK/path checks and runtime/debug TAR checks remain
in native AMD64 and ARM64 CI. No source C, nexthop patch, ABI or APT package
identity changes.

The new API first appears in build-infra #109 (`53aa20bb`). The current `.8`
entry declares the development source module version `0.0.37`; local consumers
explicitly override only this dependency to the frozen `6c43553` source.
This is an unpublished dependency, so publication requires a real infrastructure
registration after the source prerequisites merge, followed by updating this
entry's module declaration and generated overlay and repeating registry-only
consumption. The old `.25` minimum does not provide these control APIs.
The tested libnl3 module itself is always fetched through its complete registry
source recipe, without a libnl3 source override.
