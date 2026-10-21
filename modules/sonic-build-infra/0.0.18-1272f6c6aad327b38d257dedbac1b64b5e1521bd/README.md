# Shared tools and compiler support for configure/Make source builds

Register the combined reviewed source from [build-infra #53](https://github.com/securely1g/sonic-build-infra/pull/53) and [#54](https://github.com/securely1g/sonic-build-infra/pull/54).

`foreign_runtime` supplies relocatable Autotools/Libtool, protobuf/gRPC and Thrift generators, Python, Perl XML modules and Graphviz. `metadata_runtime` provides the pinned Doxygen/Aspell tools. `configure_environment.sh` selects the declared linker and sysroot-aware preprocessors, while the shared GCC toolchain preserves search flags through Libtool. The protoc wrapper carries its matching standard schemas, preserving caller include precedence and implicit current-directory lookup. These reuse the shared dependency/tool resolver. The foreign tools and kernel runtime use the shared `build_tools` APT package set. The kernel runtime retains its ARM64-to-ARM32 compatibility compiler and matching package status and library metadata for Debian dependency checks.

PI, BMv2 and DASH use the tools with their upstream configure/Make recipes to emit installed runtime and matching debug TARs. No Debian package producer or legacy Make recipe is added or changed.

The native AMD64/ARM64 registry matrix retains compiler, runtime and debug checks, adds real code-generation/relocation tests with an empty host PATH, and builds and runs Libtool C and C++ shared libraries and consumers. The version is 0.0.18 so minimum-version selection cannot silently choose the older 0.0.17 tool API.

This entry selects maintained-branch commit `1272f6c6aad327b38d257dedbac1b64b5e1521bd`, which includes merged build-infra #53 and #54. The registration is proposed through registry #87 on the tree-artifact validation stack; evaluate each consumer's selected base and current native checks separately.
