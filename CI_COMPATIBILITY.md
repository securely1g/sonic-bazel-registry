# Temporary registry branch for existing CI consumers

This branch serves `sonic-swss` PRs [#1](https://github.com/securely1g/sonic-swss/pull/1) and [#2](https://github.com/securely1g/sonic-swss/pull/2), and `sonic-buildimage` [#2](https://github.com/securely1g/sonic-buildimage/pull/2), while those consumers retain their existing module selections. It replaces their ordered lists of registry commit URLs with one reviewed branch endpoint.

It is a temporary compatibility branch, not a multi-module proposal for `main`. Move each consumer to the canonical `main` registry URL when a separately reviewed dependency update makes that possible. Keep this branch available while these consumers use it.

The starting `main` revision is `2d30a2bb2f70a0a9df9c5f545363fe3d59278452`. The entries below reproduce the version directories selected by the consumers' original registry precedence, byte for byte, including source archive URLs and integrity, overlays, patches, package locks, and presubmit files. Other version directories remain unchanged from that base.

| Module | Version | Original registry revision |
| --- | --- | --- |
| `protobuf-debian` | `3.21.12-sonic.1` | `963ff1bf04570b5acefe52fc5d6a516b40b4fd8d` |
| `sai` | `1.18.0-sonic.1` | `473dda85dc87430fddfdf12ab55a05da21748069` |
| `sonic-build-infra` | `0.0.7-91fe8246519f99838da936eee54e85208c704a4d` | `2f4012b01f7a73f24b12de64a0a9ae86a06b0e89` |
| `sonic-build-infra` | `0.0.9-c4175cb61c79b3b7b70901724fddbe2cd35ff86d` | `805f6669493f8783371e36f15b79101cf09498db` |
| `sonic-dash-api` | `0.0.0-7af4056f7393b2ccbca9fc2d9aa668251e55b0a7` | `c999f3c9ebf59c5e2d8feaae8d5010fc9204ef92` |
| `sonic-sairedis` | `0.0.0-df4319696743f4804053ab68c5af1a2b8254dcb4` | `473dda85dc87430fddfdf12ab55a05da21748069` |
| `sonic-swss-common` | `0.0.0-093a849f01722afb4730e685b3eb4f22a9bc9191` | `473dda85dc87430fddfdf12ab55a05da21748069` |

`sai 1.18.0-sonic.1` already exists on `main` with a newer overlay. This branch retains the older overlay selected by the existing consumers; both entries use the same upstream SAI archive and source checksum. Using the `main` overlay here would change their dependency graph while changing registry URLs. The canonical `main` registration is not modified.

Metadata preserves the base version lists and adds the missing selected versions. None of these versions is yanked in either its original selected metadata or the base metadata; no version is unyanked. The restored infrastructure `0.0.7` entry is needed while Bazel reads the existing transitive module graph, even though minimal version selection chooses a newer infrastructure version for SWSS.

The registry's own PR CI continues to use its checked-out registry via a local `file://` endpoint and Bazel Central Registry, with all rc files ignored. This branch adds no workflow or target changes. Some retained presubmits create DEBs; preparing and resolving this registry does not authorize executing those targets.
