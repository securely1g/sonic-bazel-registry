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
another generic foreign-build framework.

## Source provenance

The unchanged inputs and their digest receipt are published in the
[P4 source release](https://github.com/securely1g/sonic-bazel-registry/releases/tag/p4-source-inputs-20261021).

The input is the reviewed regional `p4lang-p4c_1.2.4.2.orig.tar.gz` archive:
173758549 bytes, SHA-256
`a41d616add63924a098edaab446809f543ffadfc2e40356f9b73986f324c668a`.
It is **not byte-identical** to the archive identified by the original retained
Debian descriptor. The module declares the reviewed archive's actual digest;
it does not rewrite the descriptor or claim the original digest matches.

The unchanged Debian metadata archive is 2796 bytes, SHA-256
`2a39bf04c8d084724014b71cdeb3b91dbe7a32bf1bd6cd499e5e132aa3e4cb40`.
The five SONiC patches are retained under `overlay/bazel/`, including the
upstream-authored Boost ADL fix with its original credit. The archive includes
its Protobuf/P4Runtime/Inja source inputs; FetchContent network access is disabled
and CMake consumes only those declared source trees. All other `build/**`
content is excluded; dependency source inputs also exclude CMake caches,
objects and compiled libraries. An archive audit found no compiled Protobuf
or P4C artifacts. It also contains the prebuilt AMD64
Z3 dependency used by the retained `p4testgen` recipe.

## Validation

`presubmit.json` requests source builds and artifact/runtime tests on native
AMD64 and ARM64 through the shared registry workflow. Tests compile a P4 program
to BMv2 JSON and P4Runtime metadata, compare runtime/debug build IDs, inspect
DWARF, and confirm GDB resolves a source line in the compiler.
