# Registry patch

Source: [DASH `1980c10e0d06380177d6dc411064e4d5d02724d0`](https://github.com/securely1g/DASH/commit/1980c10e0d06380177d6dc411064e4d5d02724d0), developed in [DASH #4](https://github.com/securely1g/DASH/pull/4).

`patches/0001-set-registry-module.patch` changes only `MODULE.bazel`:

- Set the source module's `0.0.1` version to the registered `0.0.3-1980c10e0d06380177d6dc411064e4d5d02724d0`.
- Remove the two root-only review-override includes and their explanatory comment. Registry consumers resolve the declared dependencies through their registry instead.

All declared dependency floors, toolchains, source inputs and package definitions are retained. The compiler/linker argument handling and its tests are already in the pinned source commit; the registry adds no runtime or test patch.

The patch is checked against the checksum-verified source archive with zero fuzz. Published DASH `.1` and `.2` contents remain unchanged.
