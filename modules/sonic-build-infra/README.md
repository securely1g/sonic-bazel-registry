# Native CPU hardening registration

`0.0.6-553b2f70f9ba77b74befdf77674894166139ddcc` registers the merged
[build-infra #6](https://github.com/securely1g/sonic-build-infra/pull/6) source.
Its CPU-specific hardening lets Common's libyang-Python dependency compile on
native AArch64. The source archive is pinned to that master commit and its
integrity; the sole registry patch aligns the module version.

The external Debian Trixie consumer builds C and C++ executables, a runtime tar,
and its detached-symbol tar on native AMD64 and ARM64. Eight explicit tests cover
both executables, CPU-specific compile options and retained common hardening,
default linker ordering, PIC, deployed content, and the debug-symbol provider.
Overlay files supply validation targets only. Existing linker search paths and
ELF stripping rules are unchanged, including the host `rpath-link` argument.

This proposal adds only the merged-source version. The superseded unmerged
`.6-7ffcef` candidate remains byte-for-byte available in immutable snapshot
`f3a7ec9888ef0269b8786f829688d6b3c1ea5abb`, retained by the
[archive branch](https://github.com/securely1g/sonic-bazel-registry/tree/archive/pr11-before-candidate-cleanup-20260928).
Earlier archived snapshots remain available to existing pins. Every version
already on registry main is preserved unchanged.

Full source-suite and installed SONiC image validation are outside this registration.
