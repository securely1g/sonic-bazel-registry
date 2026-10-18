# Distroless patch provenance and validation

`0.9.4.sonic.6` applies the complete SONiC patch set to the checksum-pinned
upstream `rules_distroless` 0.9.4 archive. The registry owns these patches and
their tests. The intermediate `.sonic.2`, `.sonic.3` and `.sonic.4` proposals
are not published by this change; existing published versions are unchanged.

| Patch | Purpose and source |
| --- | --- |
| `0001-module-version.patch` | Set the registry module version. |
| `0002-include-fragments.patch` | Retain the published `.sonic.1` fix for Protobuf `.inc` headers. |
| `0003-registry-ci.patch` | Expose lazy repositories for the registry's consumer tests. |
| `0004-pkgconfig-whitespace.patch` | Ignore empty arguments and normalize tabs in `.pc` files. Origin: [infra 7755cb7](https://github.com/securely1g/sonic-build-infra/commit/7755cb7ee3efd0eb97d16721bb64c070141f6e96). |
| `0005-multiarch-headers.patch` | Find CPU-specific include roots from declared package headers. Origin: [infra f3d9abf](https://github.com/securely1g/sonic-build-infra/commit/f3d9abf5a7d652af22575388c888ba1cd11ed26f). |
| `0006-pkgconfig-files.patch` | Export unchanged metadata, including local `.pc` aliases, through direct package, selected package and dependency-set targets. Origin: [infra 5071fef](https://github.com/securely1g/sonic-build-infra/commit/5071fef717deac95ccceff851ce7d808667c41e6). |
| `0007-concrete-packages.patch` | Prefer matching concrete packages while preserving virtual-provider fallback and version, suite and CPU filtering. Origin: [infra 12a67fd](https://github.com/securely1g/sonic-build-infra/commit/12a67fd2bc292af156f40372274c9cb3011e5c23). |
| `0008-apt-install.patch` | Install verified original DEBs with real APT/dpkg configuration scripts and triggers. Backport [rules_distroless #2](https://github.com/securely1g/rules_distroless/pull/2), commit `b3d0573b06b682a7ae3d5de20cc8215b3be3a037`, to the 0.9.4 repository/template API. Export original archives as `:deb`; retain the preceding fixes. |

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
| `install_test` | Validate installer paths, package selection, input inventory and receipt/state checks. |
| `original_deb_test` | Verify direct-import and generated package aliases retain the checksum-locked original DEB bytes. |

The four unit regressions preserve the assertions previously maintained in
`sonic-build-infra/third_party/rules_distroless`. Registry CI also builds the
real Protobuf/Lua consumers and metadata exports. It downloads and extracts
existing checksum-pinned Debian packages; it does not generate DEB packages.
The header consumers intentionally omit runtime linker inputs and do not claim
coverage of Protobuf or Lua runtime packaging.

The source rule's separate [native lifecycle CI](https://github.com/securely1g/rules_distroless/actions/runs/39084317348)
passed on AMD64 and ARM64. It checks initial configuration, generated certificate
links, alternatives, an account, library triggers and real APT install, upgrade,
remove and purge. Those end-to-end tests run against the source PR; registry CI
covers the backport's unit and import contracts. Neither result establishes full
SONiC image conversion or bit-for-bit reproducibility across fresh installs.

The installer retains package-owned `/run` files in its private filesystem.
Its validation scratch files use `/tmp`; `/run` is not a temporary mount.
This matters for Common's `/var/run/redis/sonic-db/database_config.json`.

Selected archives are reinstalled even when their version equals the installed
version. A source rebuild can change file bytes without changing its Debian
version; without `--reinstall`, APT would keep the old files and report success.
The source regression alters an installed Less executable, reinstalls the
original locked archive, and verifies that the original bytes are restored
without changing the package inventory. The latest local AMD64 lifecycle test
passes; the latest native AMD64/ARM64 CI rerun is pending.
