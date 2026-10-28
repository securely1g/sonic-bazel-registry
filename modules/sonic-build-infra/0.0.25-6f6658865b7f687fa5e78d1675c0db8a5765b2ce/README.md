# Native component tools and OCI TAR interfaces

Register the verified FRR shared infrastructure source, retaining upstream installation links and checked OCI receipts. Ordinary components use native Bazel compilation and installation TARs. No component DEB assembly or source-snapshot extension is introduced. Fixed Debian execution tools remain Bazel-managed.

Source: https://github.com/songqing-sq/sonic-build-infra-securely1g/commit/6f6658865b7f687fa5e78d1675c0db8a5765b2ce

This candidate selects `rules_distroless 0.9.4.sonic.13` with the native APT exports from [registry #146](https://github.com/securely1g/sonic-bazel-registry/pull/146), replacing the removed `.sonic.14` selection. The source also retains the Bookworm GCC 12 compiler and glibc 2.36 sysroot while using its declared architecture-matched Trixie linker.

The registry consumer retains all 32 build targets and 37 test targets on native AMD64 and ARM64. The Bookworm header/link, ABI and declared-runtime contracts are covered separately by [source PR #67](https://github.com/securely1g/sonic-build-infra/pull/67). Candidate validation requires #146's exact registry inputs; normal consumption uses maintained `main` after the dependency lands.

The registered GCC prefix-map check uses the source's existing absolute-input fixture with a registry-owned C source. Its expected path comes from that declared source's execpath, preserving the external repository directory. It checks `DW_AT_comp_dir`, `DW_AT_name` and the `__FILE__` string in `.rodata` separately; the source-root-only assertion remains unchanged in the source repository.
