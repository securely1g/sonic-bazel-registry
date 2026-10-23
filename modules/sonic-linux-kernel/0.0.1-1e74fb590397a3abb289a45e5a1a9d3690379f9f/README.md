# SONiC kernel: 0.0.1-1e74fb590397a3abb289a45e5a1a9d3690379f9f

This entry publishes `//:kernel_packages` for native AMD64 and ARM64 Trixie
VS kernels from Debian source `6.12.41-1`. The outputs are five Debian packages:
the unsigned kernel image, matching debug symbols, common headers,
architecture-specific headers, and kbuild tools. `kernel-packages.json`
(schema 3) records package metadata, output hashes, source inputs, and execution
tool identity. `//:kernel_artifacts` remains an alias for existing target users.

The source-owned rule uses the maintained Debian/SONiC source preparation and
Debian package recipes. Consumers install the real packages with their control
metadata, dependencies and maintainer scripts; matching headers and kbuild tools
support external modules. The native ABIs are `6.12.41+deb13-sonic-amd64` and
`6.12.41+deb13-sonic-arm64`.

[Kernel source #1](https://github.com/securely1g/sonic-linux-kernel/pull/1)
owns compilation, package validation, and native source/cache CI.
[Buildimage #6](https://github.com/securely1g/sonic-buildimage/pull/6)
consumes this registration and validates installed packages.

Registry presubmit runs the source-owned input, cache, launcher, artifact
publication and package-contract tests in independent native AMD64 and ARM64
consumers. Package tests create and inspect actual Debian package fixtures.
These checks do not compile a full kernel; source CI owns cold compilation and
identical-output cache-hit proof. Installed-package tests and full kernel builds
are distinct from guest boot, secure-boot signing and forwarding validation.

The module selects published shared tools
`0.0.17-306286c253b22b6bf2a75732c82bbf3d00e77cb7` from registry `main`,
registered by merged [registry #39](https://github.com/securely1g/sonic-bazel-registry/pull/39).
Source revision: `1e74fb590397a3abb289a45e5a1a9d3690379f9f`.
