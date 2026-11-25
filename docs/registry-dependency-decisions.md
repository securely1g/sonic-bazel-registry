# Registry dependency choices for the upstream sync

[PR #459](https://github.com/securely1g/sonic-bazel-registry/pull/459) aligns dependencies in the selected entries for 81 modules. The PR keeps published module names and versions and retains historical entries. The proposed `history2` branch keeps a single version directory for each module after upstream commit [`672f840a`](https://github.com/sonic-net/sonic-bazel-registry/commit/672f840ae78d6d53ffaa29fb60ff2f8147051f1e).

These selections use source ancestry, packaged targets and current consumers. Version suffixes below abbreviate the source commit. Each selected version links to its full registry entry.

The selections cover the entries published at `f2c122b9`. The refreshed base, `cd400fbb`, includes the nine subsequent releases from PRs #460–466 and #467. Those releases retain their published dependencies, including Linux Kernel 0.0.4’s Build Infra 0.0.45 pin and the shared Rust 0.0.5 APIs for DASH HA. Platform Common 1.0.1-74d0685 already selects the current Python rules in its module and test fixture. Its predecessor has no other registered consumers and retains its published dependencies. WPA 2.9.0.sonic.3 uses the FIPS 1.11 libraries and its own installed-package test helper. The older 2.9.0.sonic.2 keeps its original FIPS 0.0.6 dependency. The one-time CI exception covers 258 original module-file edits and one historical SWSS Common 0.0.9 test fixture, which uses the selected Build Infra to validate the YANG dependency.

| Module | Candidates reviewed | Selection | Reason |
| --- | --- | --- | --- |
| `sonic-swss-common` | `0.0.8-a045092`, `0.0.9-334389e`, `0.0.8-2a4ddd0` | [`0.0.8-2a4ddd0`](../modules/sonic-swss-common/0.0.8-2a4ddd070edb719f2e969a880a5cfff711e64e72/) | The final `0.0.8` source is six commits ahead of the `0.0.9` source and includes its changes. Twelve components had requested `0.0.9`. |
| `sonic-build-infra` | `0.0.42-da5f4c8`, `0.0.42-45b500f`, `0.0.44-3572639` | [`0.0.44-3572639`](../modules/sonic-build-infra/0.0.44-35726399908a3beb947174e9359f902077928289/) | The chosen source includes the kernel packaging fix from `da5f4c8`, the FIPS work from `45b500f`, and shared OCI assembly. Keep the OCI checks and the three FIPS targets described below. |
| `sonic-dash` | Native `0.0.1-d5c003d` and Make-based `0.0.3-2cbfdfa` | [`0.0.1-d5c003d`](../modules/sonic-dash/0.0.1-d5c003dd7774c2b43f275c0233acc73a0ea28d2f/) | Buildimage uses the native source and its SDK, runtime and debug targets. The native build creates an empty `saimetadatasize.h`. The SAI metadata size check from the Make-based source remains a known gap. |
| `sonic-mgmt-framework` | `1.0.1-1ca814b` and `1.0.1-07de596` | [`1.0.1-07de596`](../modules/sonic-mgmt-framework/1.0.1-07de59606b0b37a105544284405e86e1a27051bf/) | The newer source and registry overlay provide native CLI build, packaging and test targets for AMD64 and ARM64. |
| `sonic-rust-deps` | `0.0.5-dd364f2` and `0.0.5-5bf69bc` | [`0.0.5-5bf69bc`](../modules/sonic-rust-deps/0.0.5-5bf69bc0a7d9ea9f4a5606264be592867cd29d1e/) | The newer snapshot exposes seven additional crate aliases to SONiC consumers. |
| `deploy_tar_external_binary` | `0.0.0-d2283ad` and `0.0.0-8192ea3` | [`0.0.0-8192ea3`](../modules/deploy_tar_external_binary/0.0.0-8192ea3f8bbecd9982a529e547252b67dcb60804/) | Both revisions contain the same external binary test fixture. Choose the newer source commit. Build Infra resolves its development fixture from its local source tree. |
| `p4c` | BCR `1.2.5.11` and SONiC `1.2.4.2.sonic.7` | [`1.2.4.2.sonic.7`](../modules/p4c/1.2.4.2.sonic.7/) and [`1.2.5.11`](https://registry.bazel.build/modules/p4c/1.2.5.11) | Keep both existing pins. Standalone `p4_constraints` uses the public compiler. DASH uses SONiC’s packaged compiler and `p4c_bm2_ss` target. The SONiC PINS root explicitly overrides P4C to the SONiC version. |
| `rules_go` | BCR `0.64.1` and SONiC `0.65.0.sonic.2` | [`0.65.0.sonic.2`](../modules/rules_go/0.65.0.sonic.2/) | Move DASH HA and its tests to the SONiC version. It carries the relative CGo header fix and includes upstream content-derived Go and GNU build IDs. |
| `rules_python` | BCR `1.7.0`, `1.8.0`, `1.9.0` and SONiC `1.9.0.sonic.2` | [`1.9.0.sonic.2`](../modules/rules_python/1.9.0.sonic.2/) | Use the SONiC version for P4C, SWSS, Rust dependencies, SNMP agent, YANG management and YANG models. Its patch preserves wheel metadata and file modes. |

Build Infra runs `configured_install_paths_test` on AMD64 and ARM64. AMD64 also builds `dtrace` and `python_pgo_runtime`. [Build Infra validation targets](../modules/sonic-build-infra/0.0.44-35726399908a3beb947174e9359f902077928289/presubmit.json)

Thirteen module names in this catalog also exist in the Bazel Central Registry. Among these, the three public-pin decisions were P4C, Go rules and Python rules. All other same-registry pins in the selected entries converge on the selected version. The in-place edit has a one-time CI exception tied to the exact baseline and reviewed module tree.

## Follow-up after #459

The audit of `ff3d97be` found 70 older direct pins across 61 current modules. The follow-up updates 67 of those pins and their corresponding test consumers.

| Dependency | Previous | Selected | Direct pins updated |
| --- | --- | --- | ---: |
| Build Infra | `0.0.44-3572639` | `0.0.45-77ef625` | 60 |
| Rust dependencies | `0.0.5-5bf69bc` | `0.0.5-4064a81` | 4 |
| Management Common | `1.0.2-c836309` | `1.0.2-68bfd75` | 1 |
| Python rules | `1.9.0.sonic.1` | `1.9.0.sonic.2` | 1 |
| Distroless rules | `0.9.4.sonic.21` | `0.9.4.sonic.26` | 1 |

Sairedis and SWSS use `sai@1.18.0.sonic.2`. The current Sairedis source cannot compile the PON stub generated from 1.19.2 headers. After [Sairedis #18](https://github.com/securely1g/sonic-sairedis/pull/18) merges, a separate registry PR can register its landed source and move both consumers to `1.19.2.sonic.1`. Standalone `p4_constraints` continues to request public P4C `1.2.5.11`. [Sairedis #2152](https://github.com/sonic-net/sonic-sairedis/pull/2152) · [Registry #461](https://github.com/securely1g/sonic-bazel-registry/pull/461)

gNMI uses Go 1.26.0 with Management Common `68bfd75`. Management Framework keeps `c836309` and Go 1.25.9 because its certificate generator requires that SDK. The Framework source update also removes its dependency on the obsolete Common `glog.patch`. Register the compatible source after [Management Framework #7](https://github.com/securely1g/sonic-mgmt-framework/pull/7) merges.
