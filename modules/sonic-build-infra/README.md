# sonic-build-infra registry validation

## Native CPU hardening release 0.0.6

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

## Deferred historical shared-API release 0.0.7

`0.0.7-91fe8246519f99838da936eee54e85208c704a4d` retains the complete historical
source archive and registry entry for existing consumer pins. It includes the
shared sysroot and target-width SWIG APIs, together with the earlier combined
toolchain and ELF packaging changes. The independently reviewed source PRs now
have narrower contents; no single refreshed source PR has this complete tree.
Common's native YANG migration selects the CPU-only 0.0.6 entry above.

The historical entry still contains its explicit `as_needed` compatibility alias
and corresponding tests. They are preserved with the immutable source and
validation inputs, not required by current native Common or SWSS consumers.
The new source proposals remove that unused compatibility API.

The presubmit manifest exercises this exact historical module as a dependency
of a fresh consumer on native AMD64 and ARM64 Debian Trixie. It builds C++
consumers with the managed GCC toolchain, with and without the explicit alias.
Action tests check link ordering and the absence of the host `/lib/...`
`rpath-link` fallback. PIC, deployed-content, and debug-provider checks run,
and runtime and detached-symbol tar targets must build.

SWIG action-analysis tests cover Python/Go bindings, 32/64-bit target widths,
file/tree library inputs, execution-tool configuration, transitive headers, and
output groups. Each architecture builds four explicit outputs and executes
fifteen required tests. These checks do not claim ARMHF runtime execution,
complete source-suite coverage, or the nested sysroot repository fixture.
All files within the 0.0.7 version directory retain their previous bytes.
