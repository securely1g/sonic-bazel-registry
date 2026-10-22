# Complete template headers for foreign builds

This version retains the complete `0.9.4.sonic.8` patch set and exports the
C/C++ include-fragment suffixes recognized by `rules_cc` 0.2.16 from Debian
`usr/include` trees. The existing `.h`, `.hpp` and extensionless-header handling
is retained. Added forms include `.ipp`, `.tcc`, `.hh`, `.hxx`, `.h++`, `.inl`,
`.tlh`, `.tli` and `.H`; `.inc` remains supported.

P4C's graph backend includes Boost `graphviz.hpp`, which reaches
`boost/xpressive/detail/utility/chset/basic_chset.ipp`. The imported Boost
headers omitted this file, so `rules_foreign_cc` staged an incomplete include
tree and the native source build failed. Debian Boost 1.83.0-4.2 contains 310
`.ipp` files; these now enter the declared compilation context.

The regression builds and runs a CMake/Make consumer of checksum-pinned
AMD64/ARM64 Boost packages through `rules_foreign_cc`. It instantiates graph
output and regular-expression matching, exercising the real `.ipp` include
chain. An analysis regression separately requires those files in `CcInfo`, so
host-installed Boost cannot hide an incomplete import. It also covers `.tcc`
and `.hxx` classification and excludes unrelated paths and suffixes.

The native matrix retains all fourteen earlier tests and adds these two
regressions. It downloads existing SDK packages and does not create DEBs.
See [patch provenance and validation](PATCHES.md).
