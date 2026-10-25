# Producer-owned required package files

This entry publishes [sonic-build-infra #66](https://github.com/securely1g/sonic-build-infra/pull/66) for [config-engine image PR #30](https://github.com/securely1g/sonic-buildimage/pull/30).

For example, Common declares that its runtime TAR must contain
`usr/lib/{multiarch}/libswsscommon.so.0`. The shared `runtime_packages` rule checks
that declaration before emitting metadata; config-engine can reuse it instead of
listing the library again in its image policy.

| Input or action | Before | After |
| --- | --- | --- |
| Common TAR omits `libswsscommon.so.0` | Image-owned path assertions detect the omission | The producer metadata action fails before publishing a checked record |
| Config-engine normalizes database configuration from `var/run` to `run` | Image policy repeats generic package files too | Producer checks cover raw package files; the image adds its normalized location |
| Build an image whose producers have not migrated yet | Image supplies complete required paths | Existing image checks remain enforced |

All preceding patches, overlays and 29 build / 26 test selections are carried
forward. New producer/sparse-image regressions run within the existing native
AMD64/ARM64 metadata tests. Source-receipt formats, package hashes, label/module
identity checks and the existing dependency versions are preserved.

Published `0.0.22-a12bc826d6f811a157db5c7c02a2fe033896cc14` remains unchanged.
