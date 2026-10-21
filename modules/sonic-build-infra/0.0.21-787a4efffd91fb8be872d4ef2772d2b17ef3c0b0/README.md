# Declared tool launchers for foreign source builds

This entry pins the shared source at `787a4efffd91fb8be872d4ef2772d2b17ef3c0b0` and applies only the registry version suffix. It combines the static entrypoint fix from [infra60](https://github.com/securely1g/sonic-build-infra/pull/60) with the compiler-argument correction from [infra56](https://github.com/securely1g/sonic-build-infra/pull/56), while preserving the existing OCI metadata helpers.

A build tool invoked through a foreign-build symlink resolves its private runtime from the actual executable. GCC retains the original include/library search semantics while avoiding the confirmed collect2 argument-size failure under long output paths. Autoconf, Automake and Libtool remain pinned Debian tool packages.

Native AMD64 and ARM64 consumers use explicit target and execution platforms. Validation covers real Make/configure/Libtool execution, symlink/relocation/argument/exit behavior, runtime linking and runtime/debug TARs. These targets do not produce DEBs. Eight combined-source tests passed locally on native AMD64; fetched-module AMD64/ARM64 CI is required before readiness.

Direct merge gates: infra56, infra60, [registry92](https://github.com/securely1g/sonic-bazel-registry/pull/92) for native execution platforms, and [registry98](https://github.com/securely1g/sonic-bazel-registry/pull/98) for directory artifacts. The temporary base contains those shared CI changes and their reviewed fixture compatibility correction. Retarget to main after prerequisites land, preserve existing versions and revalidate.
