# sonic-build-infra 0.0.16-d5cb35774c2c091a57b02386c88d79a96ed894c4

This Draft integration contains the source-package installation controls, pinned dpkg metadata tools, Debian maintainer helpers and source-metadata rules from infra PRs #45, #46, #47 and #48. It retains grouped library metadata, service helpers and rootless permission normalization. The merged master supplies native Debian GCC, AMD64-to-ARM64 cross GCC and the shared sysroot.

Source: https://github.com/securely1g/sonic-build-infra/commit/d5cb35774c2c091a57b02386c88d79a96ed894c4

The only source patch sets this exact registry version. Published versions remain unchanged. The presubmit selects runtime/TAR and metadata checks that do not create DEB packages. This candidate remains Draft until its unmerged source features land; consumers must refresh to landed sources before review readiness.
