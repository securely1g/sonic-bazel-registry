# Declared Aspell and Doxygen launchers

Source: [build-infra #13](https://github.com/securely1g/sonic-build-infra/pull/13), commit `a7e03aeebb9d64acf5cd3867cc2fa08f5bcfa2b9`.

This version publishes the source-owned executable interfaces
`@sonic-build-infra//tools/build_tools:aspell` and `:doxygen`. Consumers select
these launchers with `cfg = "exec"` and pass their runfiles to generation actions.
The shared infrastructure owns the tools, dynamic loaders, private runtime
libraries, and prepared English dictionaries from pinned Debian package inputs.
Compiler target sysroots remain separate.

The native AMD64/ARM64 presubmit builds both launchers, executes the runtime test and sandboxed
launcher-action build check, and retains the existing C/C++ compile/link,
hardening, PIC, deployment, and debug-symbol checks. SAI metadata generation and
its retained output-baseline comparison are validated in the separate SAI
registration PR.

This additive interface is based on infrastructure master at
`2089e8cc1fd0cd83f21badfb7f6bc10e1a51da27`; it does not incorporate unrelated
pending ARMHF, wheel-layer, or DASH packaging changes. Downstream consumers that
also need those interfaces must validate a compatible combined source revision.

The immutable source archive and checksum select the exact published commit.
The production patch changes only its module version; overlays retain the
infrastructure consumer-validation targets. Existing registry versions remain
unchanged. Generated Bazel resolution locks are retained as CI artifacts.
