# Shared CLI tools and declared BFD linking

This replaces the unpublished build-infra candidate from
[registry #166](https://github.com/securely1g/sonic-bazel-registry/pull/166)
with one `0.0.26` snapshot containing two independently reviewed source features:
[build-infra #72](https://github.com/securely1g/sonic-build-infra/pull/72) provides
Framework's shared patch/XML tools; [build-infra #73](https://github.com/securely1g/sonic-build-infra/pull/73)
keeps Common's explicit BFD links on the declared compiler runtime. Both source
PR histories remain intact in the temporary combined commit
`75c6327950c6befe9606d3f2c4a7564b3437ab1c`.

Framework's klish 2.1.4 build keeps using GNU patch, xsltproc and xmllint from the
shared foreign runtime. Common's public `//goext:swsscommon` selects
`-fuse-ld=bfd`; gNMI's CGo consumer previously reached the host `/bin/ld.bfd`.
The combined toolchain exposes `ld.bfd` through its existing declared loader,
using the same pinned Debian binutils and libraries. It does not change the
compiler version or introduce another execution-tool package set.

All 35 build targets, 26 tests and validation overlays from #166 are retained.
The existing native AMD64 foreign-link test now also covers C++ BFD selection,
a failing host-linker canary, the actual backend command, target-library maps
and execution of the linked program. Shared CLI tool regressions, runtime/debug
TAR checks, and cross-compiler/tool-root checks remain included. No new DEB
output is introduced or executed; the previous sample-package fixture exclusion
is retained. Existing source architecture CI and published registry entries are
unchanged.

Keep this registration Draft while its source features and registry base are
unmerged. The version patch changes only the module identity. The cross-test
visibility patch and overlay bytes are unchanged. Consumer image acceptance is
separate from the source and registry tests.
