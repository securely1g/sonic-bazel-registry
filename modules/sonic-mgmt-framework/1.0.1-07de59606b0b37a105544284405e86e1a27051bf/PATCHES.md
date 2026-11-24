# Source adaptation

Base: securely1g/sonic-mgmt-framework@07de59606b0b37a105544284405e86e1a27051bf (unmodified upstream archive).
All adaptations are maintained downstream in this registry; they are not merged
into the source repository.

1. `0001-normalize-klish-patches.patch` converts 36 normal-format patches into
   equivalent unified patches for Bazel native patch application. The resulting
   prepared source matches the original Make patch results byte for byte.
2. `0002-native-cli.patch` replaces the Make wrapper with native CLI interfaces,
   removes its unused staging/configure paths, and updates the affected docs and
   incremental check. New native BUILD and configuration template inputs, including ARM64 compatibility, are
   supplied in `overlay/CLI/bazel/`.
3. `0003-module-and-consumer.patch` declares the prepared source, removes the
   direct foreign-cc dependency, aligns the module version, and preserves the
   registry consumer Go ownership convention.

4. `0004-arm64-targets-and-package-contract.patch` allows AMD64 and ARM64
   compilation/packaging and parameterizes the existing ELF architecture check.
   The source-owner CI workflow is not part of this fetched module adaptation.

The registry applies all patches with strip 1 after the two overlay files are
installed. No patch modifies upstream C or C++ behavior.
