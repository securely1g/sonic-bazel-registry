# sonic-build-infra 0.0.16-717519d972fe8405e4e7dec424de3058e8952b14

This Draft integration replays the declared kernel runtime from infra PR #19 on merged master. It retains pinned Kbuild/source-build tools and package metadata while using the merged native Debian GCC, AMD64-to-ARM64 cross GCC and shared sysroot.

Source: https://github.com/securely1g/sonic-build-infra/commit/717519d972fe8405e4e7dec424de3058e8952b14

The only source patch sets this exact registry version. Published versions remain unchanged. The presubmit selects runtime/TAR and metadata checks that do not create DEB packages. This candidate remains Draft until its unmerged source features land; consumers must refresh to landed sources before review readiness.

Includes the shared-library runtime search fix from sonic-build-infra PR #50. Native Debian GCC preserves transitive RPATH lookup; the imported-library regression test is selected in presubmit. This source fix is unmerged.
