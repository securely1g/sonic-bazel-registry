# Shared tools and compiler support for configure/Make source builds

Register the combined reviewed source from [build-infra #53](https://github.com/securely1g/sonic-build-infra/pull/53) and [#54](https://github.com/securely1g/sonic-build-infra/pull/54).

`foreign_runtime` supplies relocatable Autotools/Libtool, protobuf/gRPC and Thrift generators, Python, Perl XML modules and Graphviz. `metadata_runtime` provides the pinned Doxygen/Aspell tools. `configure_environment.sh` selects the declared linker and sysroot-aware preprocessors, while the shared GCC toolchain preserves search flags through Libtool. These reuse the shared dependency/tool resolver.

PI, BMv2 and DASH use the tools with their upstream configure/Make recipes to emit installed runtime and matching debug TARs. No Debian package producer or legacy Make recipe is added or changed.

The native AMD64/ARM64 registry matrix retains compiler, runtime and debug checks, adds real code-generation/relocation tests with an empty host PATH, and builds and runs a Libtool C++ shared library and consumer. The version is 0.0.18 so minimum-version selection cannot silently choose the older 0.0.17 tool API.

This is a Draft registration of unmerged source. Both infrastructure PRs must land, this entry must be repinned to their maintained-branch commit, and source plus registry consumer CI must pass before Ready.
