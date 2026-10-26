# SONiC kernel: 0.0.2-c894fafda9f0e4c9d40bb2f43bf6d41ea5bf79cc

Register `//:kernel_packages` for native AMD64 and ARM64 VS builds with Debian
source `6.12.41-1`. Bazel runs the Debian/SONiC Make packaging recipes directly in
`linux-sandbox` as an unprivileged user, using the declared relocatable compilers,
interpreters, libraries and package metadata. Kernel compilation does not launch
Docker or use root/chroot. ARM64 includes the native ARM32 compatibility-vDSO
compiler and linker.

The five outputs remain the unsigned kernel image, matching debug symbols,
common headers, architecture headers and kbuild Debian packages. Their native
ABIs are `6.12.41+deb13-sonic-amd64` and `6.12.41+deb13-sonic-arm64`.
`kernel-packages.json` (schema 3) records package metadata, output hashes,
source inputs and execution-tool identity. `//:kernel_artifacts` remains an alias.
[Buildimage #6](https://github.com/securely1g/sonic-buildimage/pull/6) consumes
these packages through its existing Make and APT/dpkg installation paths.
The public `//tools/bazel:kernel_config` setting accepts its effective Make
configuration; unsupported settings fail during analysis instead of silently
selecting a different builder. Configuration is bound to the action inputs,
manifest and source/cache verification.

[Source revision](https://github.com/securely1g/sonic-linux-kernel/commit/c894fafda9f0e4c9d40bb2f43bf6d41ea5bf79cc).
The version patch is the only source patch; historical registrations are unchanged.
The module and presubmit select shared tools `0.0.18-95cd3a9050551247063ef31eea4a48269dc50866` from
[registry #122](https://github.com/securely1g/sonic-bazel-registry/pull/122).
That shared tool version is published on the maintained registry `main`.
The kernel source is landed on the maintained `master` branch. This registration
adds its new version; one reviewed endpoint contains both versions for the
buildimage consumer.

Registry presubmit runs the source-owned input, launcher, cache verification,
artifact selection and package-contract tests in independent native AMD64 and
ARM64 consumers. Package tests create and inspect actual small Debian packages.
These checks do not compile a full kernel. [Kernel source #3](https://github.com/securely1g/sonic-linux-kernel/pull/3)
owns unprivileged cold kernel compilation and a fresh-output-directory remote-cache hit with identical
DEB hashes; buildimage CI verifies the same source/cache path and installed DEBs.
Guest boot, secure-boot signing and forwarding are separate validation.
