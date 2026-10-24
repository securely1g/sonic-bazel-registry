# Declared tool launchers for foreign source builds

Registers `0.0.21-b541569502affaf04befe9596969f3d74b979ad6` from the source launcher feature in
[infra #60](https://github.com/securely1g/sonic-build-infra/pull/60), on the landed
OCI metadata implementation. This replaces the single unpublished metadata
candidate from [registry #113](https://github.com/securely1g/sonic-bazel-registry/pull/113).

DASH's `//dash-pipeline/SAI:dash_build` invokes the pinned SAI metadata Makefile,
whose `toolsversions` target runs `make -v`. Through
`dash_build.ext_build_deps/bin/make`, the old shell wrapper searched for its
loader under `ext_build_deps/usr/lib`. The static launcher resolves the actual
executable and invokes its adjacent wrapper, retaining the declared runtime.
The source also contains the Clang correction that keeps this C-only launcher
static without changing ordinary C++ consumer behavior.

Retain all inherited package metadata, compiler, kernel, debug and runtime
checks, and add the launcher regression: 26 test targets and 29 build targets
on native AMD64 and ARM64. Registry wrappers preserve the original AMD64-to-
ARM64/ARMHF checks. The test-only visibility patch and support overlays remain;
the other patch aligns the fetched MODULE with this registry version.

The source feature and stacked registry prerequisites remain review gates.
Native CI validates this exact candidate; earlier draft results retain their
original revisions. These targets do not produce DEBs.
