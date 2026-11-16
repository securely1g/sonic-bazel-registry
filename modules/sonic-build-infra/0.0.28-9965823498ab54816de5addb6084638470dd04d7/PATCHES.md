# Registry patches for build-infra 0.0.28

The [landed source](https://github.com/securely1g/sonic-build-infra/commit/9965823498ab54816de5addb6084638470dd04d7) archive has SHA-256 `e7c8a49bb009c3392119f4c4e9883de354cd9d4996791f7ad176f80f4a7da157`. Archive verification matched all 445 file contents and Git modes to that commit.

| Patch | Purpose and origin |
| --- | --- |
| `0001-bump-version.patch` | Supplies the commit-qualified module identity `0.0.28-9965823498ab54816de5addb6084638470dd04d7` for registry resolution. The upstream module declares `0.0.28`. |
| `0002-registry-cross-test-visibility.patch` | Retains the [published 0.0.27 registry change](../0.0.27-08e0956f80574b27a9b68e72fe855cc0089058e5/patches/0002-registry-cross-test-visibility.patch). The registry's external validation targets need visibility of the existing kernel tool tests defined in [build-infra](https://github.com/securely1g/sonic-build-infra/blob/9965823498ab54816de5addb6084638470dd04d7/tools/build_tools/BUILD.bazel). This patch changes target visibility only. |

The patches apply in the listed order with strip level 1. The resulting `MODULE.bazel` matches the registry copy. The four `registry_ci/` overlay files carry the external kernel-tool and reproducible path tests. [source.json](source.json) records a separate SHA-256 integrity for each patch and overlay.
