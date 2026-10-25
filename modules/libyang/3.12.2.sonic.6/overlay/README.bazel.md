# libyang runtime and debug TARs

This module preserves the native Bazel build, SONiC validation patch and public
library interfaces from `3.12.2.sonic.1`. The runtime TAR now includes the eight
original `models/*.yang` files that upstream CMake installs under
`usr/share/yang/modules/libyang`, plus the fetched Debian `3.12.2-1` copyright
and changelog under `usr/share/doc/libyang3`.

`@libyang//:libyang_pkg` contains the source-built `libyang.so.3.9.1`, its existing
`.so.3` and `.so` links, these models and notices, and the existing combined
notices for the statically linked PCRE2/xxHash dependencies.
`@libyang//:libyang_pkg.debug_symbols` contains matching symbols from that same
linked ELF. These are filesystem TARs; they do not create DEBs, maintainer
scripts, package relationships, or dpkg installation records.

The Debian source archive is checksum-pinned. Its identity and the upstream
source hash match `libyang_3.12.2-1.dsc`; that Debian revision has no patch series.
The model files are read directly from the upstream source, and Debian notices
are read directly from the fetched archive.

`@libyang//:libyang_package_test` checks the exact eight-model inventory, modes,
root ownership and source bytes of the models/copyright/changelog, then exercises
the extracted runtime and verifies its SONAME, symlinks, hidden implementation
dependencies, matching build IDs/debuglink CRC and GDB source-line lookup.
`@libyang//:libyang_test` parses a YANG schema and JSON data through the shared
library, including PCRE2 and SONiC's `LYD_VALIDATE_NOEXTDEPS` behavior.

Registry CI selects only the runtime/debug TARs and these two tests on native
AMD64 and ARM64. It uses the landed SONiC GCC/TAR infrastructure. ARMHF and cross
execution remain outside this validation matrix.

## Generated runtime package metadata

`//:runtime_packages.json` is a generated target. The existing Debian
`control` and `changelog` define package fields; `BUILD.bazel` maps package names
to the existing Bazel TARs. The shared metadata rule inspects those target
binaries and declared dependency packages, so version constraints come from
the built artifacts and Debian tools. There is no handwritten JSON metadata
file or new DEB producer.
