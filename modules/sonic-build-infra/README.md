# sonic-build-infra registry validation

## Native CPU hardening release 0.0.6

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

The native 0.0.6 registration contains only the merged-source version. The superseded unmerged
`.6-7ffcef` candidate remains byte-for-byte available in immutable snapshot
`f3a7ec9888ef0269b8786f829688d6b3c1ea5abb`, retained by the
[archive branch](https://github.com/securely1g/sonic-bazel-registry/tree/archive/pr11-before-candidate-cleanup-20260928).
Earlier archived snapshots remain available to existing pins. Every version
already on registry main is preserved unchanged.

Full source-suite and installed SONiC image validation are outside this registration.

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
