# sonic-sairedis 0.0.0-35bd5e779be8694ef6c6082648f7e64c29ea98cc

This entry registers the existing Bazel implementation from
[sonic-sairedis PR #1](https://github.com/securely1g/sonic-sairedis/pull/1) at
source commit `35bd5e779be8694ef6c6082648f7e64c29ea98cc`. It provides the
shared C++ interfaces owned by sairedis and needed by SONiC SWSS. The registry patch
sets the module version; all implementation files come from the pinned source
archive.

This source revision selects the merged registry dependencies at `805902d076b87b41a99a4845daa17c12268a3963`: Common from merged source `5ee19a9375e667c0d507239927745de8fa29be07`, SAI metadata from registry #17, and the shared Aspell/Doxygen tools from merged infrastructure source `ff408bafc35ce0e3d7a0bd27803debdc2a921de6`. It preserves the existing shared library interfaces, external-consumer test launcher and source/archive behavior.

Previous draft registrations remain reachable through their immutable registry snapshots and archive branches; this proposal contains only its current candidate.

## Public C++ interfaces

Consumers may choose the repository name `sonic_sairedis` with `bazel_dep`.
The native registry consumer uses the module's default name `sonic-sairedis`.

| Target | Contract |
| --- | --- |
| `//meta:saimetadata_shared` | Generated SAI metadata shared library and public SAI headers |
| `//meta:saimeta_shared` | saimeta shared library, public metadata headers, and runtime dependencies |
| `//lib:sairedis_shared` | sairedis shared library, public headers, and runtime dependencies |
| `//meta:saimetadata`, `//meta:saimeta`, `//lib:sairedis` | Direct shared library outputs retained by native validation |

The shared interfaces are `CcInfo` providers backed by `cc_import`. Their
consumer dependencies expose headers and runtime libraries. The source
implementation links the static cores into the three shared libraries, so a
consumer of the public interfaces follows the shared library interface.

## Selected dependency combination

The external native consumer applies exact root selections for the SWSS
configuration being evaluated:

| Module | Selected version | Registry prerequisite |
| --- | --- | --- |
| `sonic-build-infra` | `0.0.13-ff408bafc35ce0e3d7a0bd27803debdc2a921de6` | [#27](https://github.com/securely1g/sonic-bazel-registry/pull/27) |
| `sonic-swss-common` | `0.0.0-5ee19a9375e667c0d507239927745de8fa29be07` | [#16](https://github.com/securely1g/sonic-bazel-registry/pull/16) |
| `sai` | `1.18.0-sonic.1` | [#17](https://github.com/securely1g/sonic-bazel-registry/pull/17) |
| `libnl3` | `3.7.0-sonic.2` | [#1](https://github.com/securely1g/sonic-bazel-registry/pull/1) |
| `rules_distroless` | `0.9.4-sonic.1` | [#28](https://github.com/securely1g/sonic-bazel-registry/pull/28) |

This focused compatibility check selects the native protobuf header fix from
registry PR #28. The root override prevents higher historical dotted versions
from winning module resolution. The static prerequisite base combines merged main `805902d076b87b41a99a4845daa17c12268a3963` with the exact native Distroless registration. Older source archives and registry snapshots remain unchanged for their existing consumers.

Common source `5ee19a93` sets `//tools/bazel:yang_modules` to `True` by default.
The consumer preserves this default, so Common generates its configuration
schema from the declared YANG sources. The source module explicitly selects the merged Common and infrastructure versions. The native consumer's root overrides enforce the table above, including the native Distroless patch.

## Native validation

`presubmit.json` uses the existing registry runner on native AMD64 and ARM64
Debian Trixie workers with Bazel 8.5.1. Each job builds and retains the three
shared library outputs and the existing `//lib:tests` ELF consumer, then runs
`//lib:tests_test` uncached.

The public wrapper path is explicit in the pinned source:

1. `//lib:tests_test` executes `//lib:tests`.
2. `//lib:tests` directly depends on `//lib:sairedis_shared`.
3. `//lib:sairedis_shared` exposes `//meta:saimeta_shared` through its runtime dependencies.
4. `//meta:saimeta_shared` exposes `//meta:saimetadata_shared` through its runtime dependencies.

The runner retains build outputs, uncached test evidence, and the fetched
module declarations for the selected dependencies. The companion receipt
checks the retained ELF architecture, SONAMEs, and dynamic dependencies and
compares those declarations with the selected registry entries. The final SWSS
consumer CI validates SWSS's own linkage with these interfaces.

The acceptance scope is the shared C++ interfaces and this existing consumer.
Packaging targets are outside this registration's validation scope.
