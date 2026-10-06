# Preserve Python native command results

This candidate registers the maintained `master` commit
`199a3d5aa97a6c5260cb7ca4bb5eb36cafb1a57a` landed by
[sonic-build-infra #26](https://github.com/securely1g/sonic-build-infra/pull/26).
The native Python wrapper keeps failures, buffered output and normal shutdown
handlers when it must preload its shared-library dependencies. It excludes
HWASan alongside the other sanitizer runtimes, so an ordinary Python command
does not initialize an unused sanitizer or exit during library discovery.

[sonic-buildimage #9](https://github.com/securely1g/sonic-buildimage/pull/9)
needs this through Common's Python binding for its source-built `sonic-cfggen`
tool. That command renders `docker-init.sh`; a failed render must fail the
action, and successful redirected output must be complete. This source also
includes the wheel installer and host-library search fix already adopted by
that consumer from maintained infrastructure commit `b2b9e981`.

The only registry patch changes the module version. The source archive and patch
are integrity-pinned. Published versions remain unchanged. The landed commit has the same source tree as the reviewed PR head.

The earlier `0.0.15-a238a8227e2f0664381a9596f8fd8c7074d13fa3` entry is retained
byte-for-byte temporarily because the active buildimage #9 full-image job
[112140169976](https://github.com/securely1g/sonic-buildimage/actions/runs/37422887601/job/112140169976)
selects it through this mutable registry branch. Its checkout cannot be refreshed
without replacing that attempt. Remove that compatibility entry only after the
active attempt finishes and consumers move to the landed version; until then,
this registry PR remains Draft.

The external registry consumer runs on native AMD64 and ARM64 with Debian
Trixie. It tests the native Python wrapper using a compiled extension, the
wheel installer, and the existing runtime/debug tar content, ownership and
timestamp contracts. Its explicit target set creates no Debian packages.
The buildimage consumer separately validates the real Common/config-engine
integration.

The candidate retains the source module base version `0.0.15`. Consumers must
inspect their resolved graph to verify the selected source; commit suffixes do
not sort by commit date.
