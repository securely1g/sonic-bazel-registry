# Preserve Python native command results

This candidate registers the source proposed in
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
are integrity-pinned. Published versions remain unchanged. This candidate stays
Draft while its source revision is unlanded; replace it with the actual merged
commit after the source PR lands.

The external registry consumer runs on native AMD64 and ARM64 with Debian
Trixie. It tests the native Python wrapper using a compiled extension, the
wheel installer, and the existing runtime/debug tar content, ownership and
timestamp contracts. Its explicit target set creates no Debian packages.
The buildimage consumer separately validates the real Common/config-engine
integration.

The candidate retains the source module base version `0.0.15`. Consumers must
inspect their resolved graph to verify the selected source; commit suffixes do
not sort by commit date.
