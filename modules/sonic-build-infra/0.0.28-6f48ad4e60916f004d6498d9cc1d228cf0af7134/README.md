# Native preparation for declared target runtimes

This entry registers `sonic-build-infra@0.0.28-6f48ad4e60916f004d6498d9cc1d228cf0af7134` from
[source PR #88](https://github.com/securely1g/sonic-build-infra/pull/88).
The source is based on maintained `.27`; all existing dependencies, registry
overlays and the registry visibility patch are retained. Published entries stay
unchanged.

`native_runtime_binary` prepares its declared runtime with execution-platform
Python, then executes the original target binary and loader. The target CPU
comes from Bazel constraints and every runtime ELF still undergoes the existing
architecture and loader checks. Arbitrary target Python tests retain their target
interpreter. The launcher restores caller environment values through an unlinked
file descriptor, closes that descriptor before target execution, and preserves
the caller's directory when launching the target under traced execution.

The presubmit retains all 42 build and 43 test labels from `.27` and adds the
20-case native-preparation regression as one additional test target. Source
regressions and the bounded real ARM runtime replay passed before registration;
full external-consumer acceptance remains pending in this draft.
