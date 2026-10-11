# sonic-sairedis

The current registration is `0.0.0-e9402b77ba43aee6323665921598ef67e66293f9`, from merged [source PR #1](https://github.com/securely1g/sonic-sairedis/pull/1).

It selects merged Common, SAI metadata and declared execution-tool dependencies while preserving the public C++ interfaces. Native AMD64/ARM64 validation builds the shared libraries and executes the dynamic consumer with the protobuf header fix from [Distroless #28](https://github.com/securely1g/sonic-bazel-registry/pull/28).

Only the current draft registration is included. Previous immutable registrations remain available at [the retained snapshot](https://github.com/securely1g/sonic-bazel-registry/tree/archive/pr20-before-merged-prerequisites-20261002) for consumers that still pin them.

## VS and DASH runtime packages

`0.0.1-3f7851ecfa54964758de9085c2fabdab4b3a8fa6` publishes
[sonic-sairedis #3](https://github.com/securely1g/sonic-sairedis/pull/3).
Its existing Syncd runtime/debug targets include both executables when the
caller enables DASH and supplies the `dash_sai` C++ dependency. Ordinary VS
continues to use the same public labels; VS SAI remains source-built.

Registry presubmit builds Syncd and VS SAI runtime/debug archives and runs the
existing sairedis library test on native AMD64 and ARM64. DASH SDK checks belong
to the downstream consumer because the approved cached SDK only supports
AMD64. This registry entry does not import or build those SDK producers.
Keep the entry Draft until the source prerequisite lands; refresh the source
commit and integrity before declaring dependency readiness.
