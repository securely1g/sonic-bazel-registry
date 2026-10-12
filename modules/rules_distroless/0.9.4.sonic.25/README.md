# Combined Distroless fixes

This version packages upstream `rules_distroless` 0.9.4 with all SONiC fixes:
Protobuf include fragments, pkg-config whitespace, multiarch headers, public
pkg-config metadata and concrete-package preference. The registry owns the
patches and tests; build-infra and other consumers select this module.

For example, `vim (= 2:9.1.1230-2)` now selects concrete Vim instead of vim-nox,
so Syncd's debug image can use matching package control metadata and data.
Virtual-provider fallback remains available when no concrete package satisfies
the requested version, architecture and suite.

[Patch provenance and validation](PATCHES.md) documents the complete sequence
and all nine native AMD64/ARM64 regression and integration tests. CI uses
Bazel 8.5.1 and imports existing pinned Debian packages without producing DEBs.
The intermediate `.sonic.2`, `.sonic.3` and `.sonic.4` registry proposals are
consolidated here; previously published versions retain their original contents.
