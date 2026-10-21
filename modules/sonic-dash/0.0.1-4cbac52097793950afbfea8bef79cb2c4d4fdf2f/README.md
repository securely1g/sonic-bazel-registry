# DASH BMv2 source runtime and debug TARs

Register the source implementation in [DASH #1](https://github.com/securely1g/DASH/pull/1). The module runs the source-built P4 compiler and the existing DASH generator, then wraps the upstream SAI metadata/library Make targets. It exports runtime/debug TARs and an installed SDK for [buildimage #13](https://github.com/securely1g/sonic-buildimage/pull/13), without a Debian package producer or changes to the legacy Make path.

Native AMD64 and ARM64 presubmits build all three public outputs and exercise the installed SDK, generated pipeline files, loader dependencies, build IDs, debuglink checksums, DWARF and GDB source lookup. Full source and installed-artifact validation is pending; metadata checks are not a runtime pass.

This Draft registration selects unmerged source. Its temporary base contains the reviewed PI, P4C, shared-infrastructure and C++-header prerequisites. DASH #1 and its prerequisites must land, this archive must be repinned to the landed source, the registration must target maintained main, and both native consumer jobs must pass before Ready.

The native execution-platform selection uses [registry CI #92](https://github.com/securely1g/sonic-bazel-registry/pull/92). Both host and target platforms select the declared Trixie toolchain, including P4C when it runs as a build tool. The shared runner prerequisite must land before this registration is Ready.
