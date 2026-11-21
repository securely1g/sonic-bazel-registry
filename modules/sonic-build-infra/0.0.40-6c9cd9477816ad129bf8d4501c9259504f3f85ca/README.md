# Wheel metadata for checked Python runtimes

Register merged [Infra #127](https://github.com/securely1g/sonic-build-infra/pull/127)
source `6c9cd9477816ad129bf8d4501c9259504f3f85ca` as `0.0.40-6c9cd9477816ad129bf8d4501c9259504f3f85ca`.

The DHCP relay image in [buildimage #251](https://github.com/securely1g/sonic-buildimage/pull/251)
uses `wheel_layer` outputs as inputs to `python_runtime_plan` and
`checked_python_runtime`. This source exposes the installed wheels through
`PythonRuntimeInfo`, records their distribution metadata and hashes, and accepts
the existing rules_python patched-wheel filename convention while retaining the
installed distribution version and RECORD validation.

The source module's base version remains `0.0.40`; the full merged commit identifies
this registration. Preserve all published entries, the previous registration's
cross-test visibility patch and its validation overlay. Both AMD64 and ARM64 consumer presubmits
retain the prior tools and package checks and add the owner's wheel-layer and
wheel-runtime tests. These cover metadata handoff, installed TAR contents,
dependency plans, patched wheel names and rejection of inconsistent metadata.

Consumers can select this registered version after publication and remove their
temporary review registry. This registration does not update buildimage #251.
