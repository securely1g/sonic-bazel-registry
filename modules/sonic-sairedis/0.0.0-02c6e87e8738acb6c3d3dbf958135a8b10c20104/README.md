# sonic-sairedis 0.0.0-02c6e87e8738acb6c3d3dbf958135a8b10c20104

This entry registers the existing Bazel implementation from
[sonic-sairedis PR #1](https://github.com/securely1g/sonic-sairedis/pull/1) at
source commit `02c6e87e8738acb6c3d3dbf958135a8b10c20104`. It provides the
shared C++ interfaces owned by sairedis and needed by SONiC SWSS. The registry patch
sets the module version; all implementation files come from the pinned source
archive.

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
| `sonic-build-infra` | `0.0.7-91fe8246519f99838da936eee54e85208c704a4d` | [#4](https://github.com/securely1g/sonic-bazel-registry/pull/4) |
| `sonic-swss-common` | `0.0.0-093a849f01722afb4730e685b3eb4f22a9bc9191` | [#16](https://github.com/securely1g/sonic-bazel-registry/pull/16) |
| `sai` | `1.18.0-sonic.1` | [#17](https://github.com/securely1g/sonic-bazel-registry/pull/17) |
| `libnl3` | `3.7.0-sonic.2` | [#1](https://github.com/securely1g/sonic-bazel-registry/pull/1) |
| `rules_distroless` | `0.9.4.sonic.2` | [#3](https://github.com/securely1g/sonic-bazel-registry/pull/3) |

This is a focused sairedis precheck using the current draft Distroless entry
from registry PR #3. It shares the source archive and production patches
`0001` through `0003` with SWSS's older fallback entry. The current draft adds
registry test extension declarations and overlays, so its fetched module bytes
differ. Final SWSS consumer CI retains its older entry through registry ordering
and validates that exact consumer combination.

Common source `093a849f` sets `//tools/bazel:yang_modules` to `True` by default.
The consumer preserves this default, so Common generates its configuration
schema from the declared YANG sources. The source module's minimum dependency
versions remain unchanged; the native consumer's root overrides select the
versions above for this compatibility check.

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
