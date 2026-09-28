# Native CPU hardening registration

`0.0.6-553b2f70f9ba77b74befdf77674894166139ddcc` registers the merged fix that lets native
AArch64 compile Common's libyang-Python dependency with a supported CPU hardening
option. Its source is commit `553b2f70f9ba77b74befdf77674894166139ddcc` on master after
[build-infra #6](https://github.com/securely1g/sonic-build-infra/pull/6) merged.

The previous `0.0.6-7ffcef1849fb7c96ef99f5d64339b87eac0beefd` entry remains byte-for-byte
unchanged. Both source commits have the same Git tree; the new version aligns
source provenance with the merged commit and introduces no behavior change.

The external Debian Trixie consumer builds C and C++ executables, a runtime tar,
and its detached-symbol tar on native AMD64 and ARM64. Eight explicit tests cover
both executables, CPU-specific compile options and retained common hardening,
default linker ordering, PIC, deployed content, and the debug-symbol provider.
The entry does not add a compatibility feature or change master's linker search
paths or ELF stripping rules. In particular, master's host `rpath-link` argument
remains; this validation does not claim that path was removed.

The previous `0.0.6-4fb4dca08ea10f7d60e9d217f476fd9a2f975ff2` entry was only in
unmerged PR snapshots. Its complete immutable entry remains accessible at
`5cac5fc836f46e79c9210448a7437c5011d8bafe` and the
[archive branch](https://github.com/securely1g/sonic-bazel-registry/tree/archive/pr-11-before-cpu-only-20260928).
Existing pins can still retrieve that snapshot unchanged. No version on registry
main is removed or rewritten.

The source archive is pinned by commit and integrity; its sole registry patch
aligns the module version. Overlay files contain validation targets only. Full
source-suite and installed SONiC image validation are outside this registration.
