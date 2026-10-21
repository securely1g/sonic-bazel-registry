# P4C 1.2.4.2 for SONiC

This producer retains SONiC's `p4lang-p4c` 1.2.4.2-3 CMake/Make build
and source patches. Bazel declares its sources, compiler, build tools and
libraries, then packages the installed files directly into runtime/debug TARs.
No Debian package is generated and the existing Make build is unchanged.

## Targets

| Target | Contract |
| --- | --- |
| `@p4c//:p4c_pkg` | Stripped compiler programs, installed Python driver/configuration and P4 includes |
| `@p4c//:p4c_pkg.debug_symbols` | Matching ELF symbols indexed by GNU build ID |
| `@p4c//:p4c_bm2_ss` | Executable compiler with declared libraries, C preprocessor and private P4 include tree; usable as an action tool with `cfg = "exec"` |
| `@p4c//:configuration` | CMake cache and compilation database retained as CI artifacts |
| `@p4c//:package_test` | Compiler invocation on a v1model program and installed runtime/debug pair validation |

The build retains BMV2, eBPF, uBPF, DPDK, graph, P4 test and P4TC backends,
garbage collection, GMP and static Protobuf. Documentation, Google Tests and
multithreading remain disabled. As in the Debian recipe, AMD64 includes
`p4testgen`; ARM64 disables test tools because the source archive supplies only
an AMD64 Z3 4.11.2 dependency. Runtime and debug TARs are made from one
`-O2 -g` build, with build IDs and hardening flags retained.

## Why this registry overlay exists

The Bazel Central Registry was checked before implementation. It offers P4C
`1.2.5.11` and `1.2.5.11.bcr.1`, whose upstream native Bazel graph does not
provide SONiC's 1.2.4.2 baseline or the retained CMake installation contract.
This implementation follows the user's selected P4 configure/Make-through-Bazel
approach. It reuses `rules_foreign_cc`, the shared SONiC GCC/build-tools rules,
APT C++ dependencies, and shared runtime/debug TAR packaging. It does not add
another generic foreign-build framework. Host `ccache` discovery is explicitly
disabled; Bazel owns the build cache. `rules_distroless` 0.9.4.sonic.9 supplies
the complete Boost template-header inputs required by the graph backend.

## Source provenance

The compiler comes directly from upstream P4C commit
[`624c6be8076881e9af1e2f7d7691bc6c4416f4b1`](https://github.com/p4lang/p4c/commit/624c6be8076881e9af1e2f7d7691bc6c4416f4b1),
with checksum-pinned upstream libbpf submodule
`051a4009f94d5633a8f734ca4235f0a78ee90469` restored separately.
The reviewable `overlay/bazel/native-protoc.patch` builds native `protoc` from
Protobuf sources and adds its include path to P4Runtime generation. These two
changes were recovered from the retained source bundle; they are explicit
patches against primary source here.

An audit compared every compiler file and symlink outside Git metadata,
`build` and `debian`, including executable permissions. All 13,118 files match
the retained compiler tree after that patch and the libbpf checkout. The receipt
is [source-provenance.json](source-provenance.json). The seven older upstream
Debian files are replaced by the selected 1.2.4.2-3 metadata before applying the
five retained SONiC patches, including the upstream Boost ADL fix with its credit.
No Debian build or installation commands execute.

The [P4 source release](https://github.com/securely1g/sonic-bazel-registry/releases/tag/p4-source-inputs-20261021)
preserves the retained bundle and Debian metadata with their digest receipt.
The retained `p4lang-p4c_1.2.4.2.orig.tar.gz` is 173758549 bytes, SHA-256
`a41d616add63924a098edaab446809f543ffadfc2e40356f9b73986f324c668a`.
It is a recovered bundle with the native-protoc adaptations, **not a pristine
upstream archive** and **not byte-identical** to the original retained Debian
descriptor's archive. This producer extracts only its Protobuf, P4Runtime and
Inja source trees and its AMD64 Z3 input. Its compiler tree is not extracted.

The unchanged Debian metadata archive is 2796 bytes, SHA-256
`2a39bf04c8d084724014b71cdeb3b91dbe7a32bf1bd6cd499e5e132aa3e4cb40`.
FetchContent network access is disabled. CMake consumes only the declared source
trees, excluding Git metadata, CMake caches, objects and compiled libraries.
An archive audit found no compiled Protobuf or P4C artifacts. The retained
`p4testgen` recipe's prebuilt AMD64 Z3 static library is declared explicitly;
ARM64 keeps that optional test tool disabled.

## Validation

`presubmit.json` requests source builds and artifact/runtime tests on native
AMD64 and ARM64 through the shared registry workflow. Tests compile a P4 program
to BMv2 JSON and P4Runtime metadata, compare runtime/debug build IDs, inspect
DWARF, and confirm GDB resolves a source line in the compiler.
