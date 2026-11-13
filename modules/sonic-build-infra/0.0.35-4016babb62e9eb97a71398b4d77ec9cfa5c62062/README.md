# Shared Trixie APT collection for DHCPMon

Register `sonic-build-infra@0.0.35-4016babb62e9eb97a71398b4d77ec9cfa5c62062` for [DHCPMon #1](https://github.com/securely1g/sonic-dhcpmon/pull/1). [Infrastructure #102](https://github.com/securely1g/sonic-build-infra/pull/102) adds the `dhcpmon_debian` collection to the shared APT lock. It supplies development libraries and runtime package metadata for native AMD64 and ARM64 builds.

The source archive contains the shared lock. The version patch sets the registered module identity. The cross-test visibility patch, test overlays and native AMD64/ARM64 presubmit targets are unchanged from the preceding publication.
