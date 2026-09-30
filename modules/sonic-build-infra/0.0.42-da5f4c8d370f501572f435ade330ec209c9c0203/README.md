# Shared SAI generator packages

This version registers [build-infra #8](https://github.com/securely1g/sonic-build-infra/pull/8)
at source commit `e8b05b109187345586a18628ad01626e69c02fbe`.
It provides Doxygen, Aspell, and English dictionaries through a separate
`build_tools` APT package set so SAI can use shared package resolution. The
compiler `sysroot` set retains its system library roots. Both sets use the same
pinned Debian Trixie sources and support native AMD64 and ARM64 consumers.

The existing native AMD64/ARM64 registry consumer checks cover C/C++ compilation,
CPU hardening, linking, PIC, deployed contents, and matching debug packages.
[SAI #17](https://github.com/securely1g/sonic-bazel-registry/pull/17) validates the
generator inputs by preparing dictionaries, running metadata generation, and
comparing its outputs with the retained sairedis baseline. Its consumer selects
the tool packages in the execution configuration.

The source archive and checksum identify the exact source commit. The only
production patch aligns its MODULE.bazel version with this registry entry;
overlays supply the existing infrastructure validation targets. Previously
published versions are preserved.
