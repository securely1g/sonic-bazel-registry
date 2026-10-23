# sonic-build-infra 0.0.17-306286c253b22b6bf2a75732c82bbf3d00e77cb7

Provide the native AMD64 and ARM64 execution runtime used by [kernel #1](https://github.com/securely1g/sonic-linux-kernel/pull/1), from merged [infra #52](https://github.com/securely1g/sonic-build-infra/pull/52). ARM64 includes the pinned ARM32 compiler and linker needed by the kernel compatibility vDSO. The source retains the AMD64 runtime and maintained native/cross GCC toolchains from the infrastructure target branch.

Source: https://github.com/securely1g/sonic-build-infra/commit/306286c253b22b6bf2a75732c82bbf3d00e77cb7

The version patch is the only source patch. Presubmit builds the runtime provenance manifest and checks rootfs metadata, the kernel runtime, transitive runtime loading and shared-library layout on native AMD64 and ARM64 runners. The runtime check compiles and runs a native ELF executable; ARM64 also compiles and links an ARM32 compatibility-vDSO probe. These checks do not create Debian packages.

The source commit is the landed revision on infrastructure `master`. All published registry versions remain unchanged. Full kernel compilation and cache-hit verification belong to the kernel source CI.
