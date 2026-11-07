# Native runtime preparation and shared image APT compatibility

This entry registers `sonic-build-infra@0.0.28-23b398c24d3b53e756785d1ed4c0ba5f62e9cdb1` from
[source #88](https://github.com/securely1g/sonic-build-infra/pull/88), which
preserves the original native-runtime preparation commit and incorporates
[source #90](https://github.com/securely1g/sonic-build-infra/pull/90).
It refreshes the one unpublished `.28` candidate. The published `.27` entry,
existing registry overlays, and visibility patch remain unchanged.

Before this change, an AMD64 build preparing an ARM64 test runtime launched
target Python under emulation. `native_runtime_binary` now prepares that runtime
with execution-platform Python, then runs the original target executable and
loader. Target architecture and loader checks remain in place. Arbitrary target
Python tests retain their target interpreter; caller environment values and the
working directory are preserved by the existing runtime launcher.

The shared APT lock also supports the image and library consumers selected by
[buildimage #133](https://github.com/securely1g/sonic-buildimage/pull/133).
Previously, replacing its four image locks with the shared lock left Sysmgr and
older libnl/libyang request groups unavailable, and the shared Syncd debug group
selected `vim-nox` instead of the image's existing `vim` payload. The shared
requests now include the missing groups and a distinct
`syncd_vs_vim_debug_debian` set. Existing Syncd consumers keep their `vim-nox`
set. All 2,184 previously shared package identities and checksums are retained;
the canonical Orchagent closure additionally contains `lsb-base` metadata and
documentation. Bookworm consumers can import the declared native-build inputs.

## Validation

The registry presubmit retains all 42 build targets and 43 test targets from
published `.27`, plus the native-preparation regression introduced by the
original `.28` candidate: 42 builds and 44 tests on native AMD64/Trixie.

The new `//apt/tests/integration:bookworm_library_import_test` runs in the source
repository's normal Bookworm phase on AMD64 and ARM64. It is not added to the
Trixie registry test list, where its platform constraint would skip it. The
exact combined source passed the native AMD64 Bookworm smoke and preparation
regression locally. Registry consumer and image validation are recorded
separately in their PRs.
