# Registry patches for build-infra 0.0.29

The [source archive](https://github.com/securely1g/sonic-build-infra/commit/4854fb00e85201701b566169ccf298de8ad4d1ed) has SHA-256 `0fad0b948d483932e3e55f139cc0803c53a3097e6e821b4b633a0bd91da13207`. Its 448 tracked file contents and modes match the pinned Git tree.

| Patch | Purpose |
| --- | --- |
| `0001-bump-version.patch` | Qualifies the source module's 0.0.29 identity with the exact Git commit for registry consumers. |
| `0002-registry-cross-test-visibility.patch` | Carries forward the [published kernel tool test visibility](../0.0.28-9965823498ab54816de5addb6084638470dd04d7/patches/0002-registry-cross-test-visibility.patch) needed by registry validation. |

The patches apply in order with strip level 1, and the resulting module matches the registry copy. The four registry-only kernel and reproducible-path fixtures retain their published overlay checksums. [Archive, patch and overlay integrities](source.json)
