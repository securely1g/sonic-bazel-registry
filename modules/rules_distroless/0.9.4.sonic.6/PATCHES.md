# Distroless patch provenance and validation

`0.9.4.sonic.6` applies the complete SONiC patch set to the checksum-pinned
upstream `rules_distroless` 0.9.4 archive. The registry owns these patches and
their tests. The intermediate `.sonic.2`, `.sonic.3` and `.sonic.4` proposals
are not published by this change; existing published versions are unchanged.
This entry retains `.sonic.5` and adds only the provider advertisement repair
and its native shared-library regression.

`Introduced in` identifies the first published registry version containing the
patch's behavior; new patches show their proposed version. Later revisions
may update a patch. `0.9.4-sonic.1` is the historical spelling before the
registry adopted dotted versions; `.sonic.2` through `.sonic.4` were unpublished
proposals and are not counted as releases.

| Patch | Introduced in | Purpose and source |
| --- | --- | --- |
| `0001-module-version.patch` | `0.9.4-sonic.1` | Set the registry module version. |
| `0002-include-fragments.patch` | `0.9.4-sonic.1` | Retain the published `.sonic.1` fix for Protobuf `.inc` headers. |
| `0003-registry-ci.patch` | `0.9.4-sonic.1` | Expose lazy repositories for the registry's consumer tests. |
| `0004-pkgconfig-whitespace.patch` | `0.9.4.sonic.5` | Ignore empty arguments and normalize tabs in `.pc` files. Origin: [infra 7755cb7](https://github.com/securely1g/sonic-build-infra/commit/7755cb7ee3efd0eb97d16721bb64c070141f6e96). |
| `0005-multiarch-headers.patch` | `0.9.4.sonic.5` | Find CPU-specific include roots from declared package headers. Origin: [infra f3d9abf](https://github.com/securely1g/sonic-build-infra/commit/f3d9abf5a7d652af22575388c888ba1cd11ed26f). |
| `0006-pkgconfig-files.patch` | `0.9.4.sonic.5` | Export unchanged metadata, including local `.pc` aliases, through direct package, selected package and dependency-set targets. Origin: [infra 5071fef](https://github.com/securely1g/sonic-build-infra/commit/5071fef717deac95ccceff851ce7d808667c41e6). |
| `0007-concrete-packages.patch` | `0.9.4.sonic.5` | Prefer matching concrete packages while preserving virtual-provider fallback and version, suite and CPU filtering. Origin: [infra 12a67fd](https://github.com/securely1g/sonic-build-infra/commit/12a67fd2bc292af156f40372274c9cb3011e5c23). |
| `0008-ccinfo-providers.patch` | `0.9.4.sonic.6` | Advertise the existing `CcInfo` provider so native `cc_shared_library` visits imported runtime-library metadata. |

These are SONiC-maintained adaptations, not imported upstream commits.
[Upstream #220](https://github.com/bazel-contrib/rules_distroless/pull/220)
contains Song Qing's related multiarch proposal. The concrete-package fix has
related proposals in [#212](https://github.com/bazel-contrib/rules_distroless/issues/212)
and [#265](https://github.com/bazel-contrib/rules_distroless/issues/265).
[Upstream #285](https://github.com/bazel-contrib/rules_distroless/pull/285)
proposes the metadata exports against newer upstream code; this entry retains
the existing 0.9.4 implementation. Patch headers retain the detailed provenance.

## Required native tests

`presubmit.json` runs every test below in a fresh external Bazel 8.5.1 consumer
on both AMD64 and ARM64. Every test exercises the same registry-fetched module
with the full patch set applied; there is no separately patched test archive.

| Tests | Contract |
| --- | --- |
| `protobuf_headers_test` | Compile real pinned Debian Protobuf headers, including `.inc` fragments. |
| `lua_headers_test`, `multiarch_test` | Compile real Lua headers and check include-root discovery, deduplication and unrelated-path exclusion. |
| `pkgconfig_test` | Repeated spaces, tabs, empty substitutions and empty Libs/Cflags produce no empty arguments. |
| `pkgconfig_selection_test` | Metadata includes the selected CPU and `Architecture: all`, excludes the other CPU, maps metadata/data labels consistently and handles empty dependencies. |
| `pkgconfig_files_test` | Direct, package and dependency-set exports preserve every original Lua `.pc` file and alias byte-for-byte. |
| `architecture_amd64_test`, `architecture_arm64_test` | Generated dependency-set selection matches each CPU. |
| `concrete_packages_test` | Concrete preference, exact versions, suite filtering, unmatched versions, virtual-only fallback and `Architecture: all`. |
| `native_shared:runpath_test` | Link a native shared library against separate unversioned link and versioned runtime imports; load it with RUNPATH, no RPATH and no loader environment overrides. |

The four unit regressions preserve the assertions previously maintained in
`sonic-build-infra/third_party/rules_distroless`. Registry CI also builds the
real Protobuf/Lua consumers and metadata exports. It downloads and extracts
existing checksum-pinned Debian packages; it does not generate DEB packages.
The header consumers intentionally omit runtime linker inputs and do not claim
coverage of Protobuf or Lua runtime packaging.

## Native shared-library regression

The new fixture builds small C libraries rather than Debian packages. A
`cc_import` exposes only an unversioned link alias; the actual versioned file
is exposed through `so_library` and `cc_deb_library` in another directory.
The final executable loads a native `cc_shared_library` from its declared
runfiles with `dlopen`, calls through it to the imported library, and checks
that both the executable and middle
library have RUNPATH with no RPATH. It rejects `LD_LIBRARY_PATH` and
`LD_PRELOAD` overrides. It verifies that the executable has no direct
`DT_NEEDED` entry for either library and only the middle library needs the
imported leaf. The test executable and native shared library explicitly enable new dtags.

This isolates native Bazel provider traversal from system package installation
and from any global RPATH compatibility flag. It does not claim to solve
indirect runtime dependencies of unmodified Debian libraries; those still
need an appropriate installed or otherwise declared runtime environment.

The provider repair was developed locally after the Common native shared
library failed to find `libhiredis.so.1.1.0`: its unversioned development import
was present, but the separate runtime package's directory was missing from
the shared library's search path. Upstream
[`so_library.bzl`](https://github.com/bazel-contrib/rules_distroless/blob/403a8b5dc7fe80d31156d92f9c14789f9f547a50/apt/private/so_library.bzl)
and
[`cc_deb_library.bzl`](https://github.com/bazel-contrib/rules_distroless/blob/403a8b5dc7fe80d31156d92f9c14789f9f547a50/apt/private/cc_deb_library.bzl)
still omit the provider advertisement at that checked revision.
