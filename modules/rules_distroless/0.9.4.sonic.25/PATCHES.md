# Distroless patch provenance and validation

`0.9.4.sonic.14` uses the same checksum-pinned upstream 0.9.4 archive as published
`0.9.4.sonic.12`. It inherits patches `0002` through `0014` byte-for-byte,
including the installer, lock importer and compiler/header fixes. Patch `0001`
changes only the module version; patch `0015` adds account preservation for
[buildimage #33](https://github.com/securely1g/sonic-buildimage/pull/33).
No published entry is modified.

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
| `0009-pkgconfig-field-separators.patch` | `0.9.4.sonic.7` | Parse colon-tabs and colon-without-space fields; distinguish variable assignments from separators inside values. |
| `0010-pkgconfig-quoting.patch` | `0.9.4.sonic.8` | Decode quotes and backslash escapes in expanded flags and path variables; preserve spaces within arguments. |
| `0011-template-headers.patch` | `0.9.4.sonic.9` | Include the remaining rules_cc-supported header fragments under `usr/include`, including Boost `.ipp` files. |
| `0012-headerless-includes.patch` | `0.9.4.sonic.14` | Export the package include root only when it owns declared compiler inputs; preserve all linker and transitive contexts. |
| `0013-import-apt-lock.patch` | `0.9.4.sonic.11` | Import exact package archives and dependency graphs from one reviewed lock; include the extension's unit regressions. Origin: [build-infra #59](https://github.com/securely1g/sonic-build-infra/pull/59). |
| `0014-apt-install.patch` | `0.9.4.sonic.12` | Add optional APT/dpkg installation and original-DEB aliases that preserve locked-import repository prefixes. Installer source: [rules_distroless fork PR #2](https://github.com/securely1g/rules_distroless/pull/2), commit `b3d0573b06b682a7ae3d5de20cc8215b3be3a037`, previously proposed in closed registry #72 and reused in #110. |
| `0015-preserve-base-accounts.patch` | `0.9.4.sonic.14` (proposed) | Preserve inherited OCI users and groups when adding service accounts. Source: [upstream #290](https://github.com/bazel-contrib/rules_distroless/pull/290), commit `d503c1141d3759390dc78ffbb99de33b7d4f4619`; adapted MODULE integration from [registry #128](https://github.com/securely1g/sonic-bazel-registry/pull/128). |

These are SONiC-maintained adaptations; each patch records its source.
[Upstream #220](https://github.com/bazel-contrib/rules_distroless/pull/220)
contains Song Qing's related multiarch proposal. The concrete-package fix has
related proposals in [#212](https://github.com/bazel-contrib/rules_distroless/issues/212)
and [#265](https://github.com/bazel-contrib/rules_distroless/issues/265).
[Upstream #285](https://github.com/bazel-contrib/rules_distroless/pull/285)
proposes the metadata exports against newer upstream code; this entry retains
the existing 0.9.4 implementation. Patch headers retain the detailed provenance.

## Required native tests

`presubmit.json` runs every test below from a fresh copy of the independent
`tests/integration` Bazel 8.5.1 consumer
on both AMD64 and ARM64. The dependency and archive tests exercise the same
registry-fetched module with the full patch set applied; there is no separately
patched test archive. The fixture test checks its maintained generation helper.

| Tests | Contract |
| --- | --- |
| `protobuf_headers_test` | Compile real pinned Debian Protobuf headers, including `.inc` fragments. |
| `lua_headers_test`, `multiarch_test` | Compile real Lua headers and check include-root discovery, deduplication and unrelated-path exclusion. |
| `pkgconfig_fields_test` | Fields with spaces, tabs or no separator whitespace; variable URLs and colon-separated values; fields containing equals signs; boundary whitespace. |
| `xtables_headers_test` | Compile actual pinned Debian xtables headers using the include directory exported from colon-tab fields. |
| `pkgconfig_quotes_test`, `libpcap_headers_test` | Decode real libpcap quoted variables, quoted and escaped spaces, literal quotes/backslashes; compile pinned native libpcap headers. |
| `pkgconfig_test` | Repeated spaces, tabs, empty substitutions and empty Libs/Cflags produce no empty arguments. |
| `pkgconfig_selection_test` | Metadata includes the selected CPU and `Architecture: all`, excludes the other CPU, maps metadata/data labels consistently and handles empty dependencies. |
| `pkgconfig_files_test` | Direct, package and dependency-set exports preserve every original Lua `.pc` file and alias byte-for-byte. |
| `architecture_amd64_test`, `architecture_arm64_test` | Generated dependency-set selection matches each CPU. |
| `concrete_packages_test` | Concrete preference, exact versions, suite filtering, unmatched versions, virtual-only fallback and `Architecture: all`. |
| `native_shared:runpath_test` | Link a native shared library against separate unversioned link and versioned runtime imports; load it with RUNPATH, no RPATH and no loader environment overrides. |

The four unit regressions preserve the assertions previously maintained in
`sonic-build-infra/third_party/rules_distroless`. Registry CI also builds the
real Protobuf/Lua/xtables consumers and metadata exports. It downloads and extracts
existing checksum-pinned Debian packages; it does not generate DEB packages.
The header consumers intentionally omit runtime linker inputs and do not claim
coverage of Protobuf, Lua or xtables runtime packaging.

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

## pkg-config separator regression

The native iproute2 build in [registry PR #64](https://github.com/securely1g/sonic-bazel-registry/pull/64)
failed to compile `tc/em_ipset.c`: the Debian `libxtables-dev` import declared
its headers but had no include root. Its `xtables.pc` uses `Cflags:` followed
by a tab. Upstream 0.9.4 only recognized a literal colon-space. The existing
`0004` patch normalizes whitespace within already parsed flags and cannot fix
this earlier field parsing step.

The new patch uses the first `:` or `=` to identify the line's syntax and trims
boundary whitespace from keys and values. This preserves colons inside variable
values and equals signs inside field values. Parser tests cover both forms,
including URLs and compiler definitions. The native fixture imports the real
AMD64/ARM64 `libxtables-dev` and `libxtables12` 1.8.11-2 packages with reviewed
SHA-256 hashes. Its header-only compilation context excludes runtime linker
inputs; it validates the metadata and headers, not runtime installation.

## pkg-config quoting regression

The BMv2 source build imports Debian libpcap 1.10.5-2. Its metadata wraps
`prefix`, `includedir` and `libdir` in quotes, including nested substitutions.
The old `_tokens` implementation only split whitespace, so generated include
paths and RPATH flags retained literal quotes. `rules_foreign_cc` then rejected
its malformed directory-copy arguments before compiling BMv2.

Patch `0010` tokenizes the expanded flag fields with single/double-quote and
backslash state. Whitespace only separates unquoted arguments; quote characters
are removed, and the shell's limited double-quote backslash rules are preserved.
Path variables use the same lexer without word splitting. Unterminated quotes
or escapes produce an explicit metadata error. This is lexical parsing only;
it does not evaluate shell expressions or introduce shell execution.

The libpcap fixtures and general quoting fixtures were compared with native
pkg-config 1.8.1 with system include/library filtering disabled. The native
header consumer imports checksum-pinned AMD64/ARM64 libpcap 1.10.5-2 packages
and compiles through their generated compilation context. Existing metadata,
header and runtime-provider tests remain enabled.

This is a SONiC-maintained repair. The upstream parser at
[`3999d9ca`](https://github.com/bazel-contrib/rules_distroless/blob/3999d9ca8e7eb83224fcb947dbda31e5f0e55382/apt/private/pkgconfig.bzl)
still splits flag fields by spaces and does not decode shell quoting.

## Template-header regression

The retained P4C 1.2.4.2 graph backend failed at native compilation because
`boost/xpressive/detail/utility/chset/basic_chset.ipp` was missing from the
`rules_foreign_cc` dependency directory. The actual pinned Debian
`libboost1.83-dev` 1.83.0-4.2 archive contains that file and 309 other `.ipp`
files; the generated `CcInfo` omitted all of them.

The importer now recognizes the additional header suffixes supported by
[`rules_cc` 0.2.16](https://github.com/bazelbuild/rules_cc/blob/0.2.16/cc/common/cc_helper_internal.bzl)
inside installed include trees. This is a SONiC-maintained importer repair;
no Boost or P4C source workaround is applied.

`template_headers:declared_headers_test` requires the real Xpressive and
Spirit `.ipp` headers in the imported compilation context and checks `.tcc`
and `.hxx` handling, path boundaries and unrelated extensions.
`template_headers:foreign_headers_test` builds and runs graph-output and
regex operations using the imported Boost headers through CMake/Make and
`rules_foreign_cc`. It also exercises standard-library vector templates.
The explicit analysis assertions ensure host Boost installations cannot mask
missing declarations. Both tests run on native AMD64 and ARM64 alongside all
fourteen retained regressions.

## Headerless runtime-context regression

The BMv2 source graph contains 81 runtime package contexts advertising an
include directory despite owning no headers. The source build's long compiler
command exceeded Linux's per-environment-string limit when GCC spawned cc1plus.
The importer now adds its include root only when `hdrs` or
`additional_compiler_inputs` is nonempty. It does not filter library arguments,
change their order, or remove declared dependency inputs.

Four CcInfo regressions check empty, direct, additional and transitive header
contexts and unchanged linker flags. Restoring the unconditional include root
makes the headerless regression fail while the other three controls pass.
All sixteen prior native tests are retained. The remaining GCC command-size
issue with long build paths requires a separate compiler adapter fix; this
entry alone does not establish that the complete BMv2 source build passes.

## Import one reviewed APT lock

The `apt.import_lock(lock = "//image:apt.lock.json")` tag replaces a second
generated MODULE file repeating every package version. It reads exact archive
URLs, hashes and dependency graphs without resolving package indexes or
rewriting the lock. Existing `deb_import`, `deb_postfix` and dependency-set
rules still create independent data/control targets and complete closures.
C++ discovery remains on `apt.install`, which has Contents-index information
that runtime locks do not contain.

`0013-import-apt-lock.patch` retains the implementation and test hunks originally
proposed as `third_party/rules_distroless/patches/0001-import-apt-lock.patch`
in build-infra #59. Maintain further changes here; the patch header preserves
its original authorship and records the registry ownership.
The archive integration test and reviewed lock live in `tests/integration`,
whose own `MODULE.bazel` imports the registry dependency and registers the sample
repositories. They are ordinary test files, not dependency overlays or patches.
The former `0014-locked-import-tests.patch` is removed: test repository setup no
longer changes the dependency's MODULE file.
The new Starlark tests cover missing dependencies, identities, hashes,
architectures, cycles and set selection. The archive integration test checks
locked versions, independent data/control labels, architecture-independent
packages, full closures and identical contents from separate imports.
All twenty prior tests and six build targets remain selected; the four
locked-import tests and fixture-regeneration test run on native AMD64 and
ARM64. No test creates a DEB.

The original fixture-selection helper is retained byte-for-byte as
`tests/integration/tools/select_lock_fixture.py`; see
[fixture refresh instructions](README.md#refresh-the-reviewed-lock-fixture).
The ordinary Bazel `//:fixture_regeneration_test` checks that the helper
reproduces the reviewed lock byte-for-byte without changing its input.
The shared registry runner checks host/userspace architecture and unchanged
recipe inputs and provides archive integrity, generated lock, fetched MODULE
and uncached test evidence. No module-specific CI driver is required.

## Install the reviewed Debian archives

`0014-apt-install.patch` retains the installer implementation and tests from
registry #110 and the lock-prefix compatibility previously composed in #114.
It leaves the inherited `0013` patch unchanged. Original `:deb` targets keep
both archive bytes and the repository prefix chosen by each independent lock
import, so APT receives the exact reviewed package instead of an unrelated
archive target.

For example, configuring `ca-certificates` runs its package scripts and triggers,
creating `/etc/ca-certificates.conf` and certificate hash links. Extracting its
payload and writing a synthetic package-status file does not perform that work.
The optional installer produces a configured filesystem TAR plus an installation
receipt; it installs existing DEBs and does not produce new DEB packages.

All 25 tests and six build targets from published `.sonic.11` remain selected.
`apt/private:install_test` checks installer input validation and helper
behavior. `registry_ci:original_deb_test` checks direct/package alias identities.
The independent `archive_contract_test` additionally checks the exact libc6 DEB
hash from each of two lock prefixes, while `fixture_regeneration_test` continues
to verify the reviewed lock generator. These 27 inherited installer and lock
tests run uncached on native AMD64 and ARM64 alongside the account tests below. These checks validate this registry interface; the consuming
image must separately validate the complete installed filesystem.

## Preserve inherited users and groups

`0015-preserve-base-accounts.patch` carries the public account-layer API and five
regression targets reviewed in [registry #128](https://github.com/securely1g/sonic-bazel-registry/pull/128)
and proposed in [upstream #290](https://github.com/bazel-contrib/rules_distroless/pull/290),
referencing upstream #278. The implementation and regression hunks match source
commit `d503c1141d3759390dc78ffbb99de33b7d4f4619` byte-for-byte. Its MODULE hunk
updates the installer's existing Python dependency to 1.7.0 and declares Python
3.11 without changing BSD tar 0.10.4. Retain the local patch until a selected
upstream release includes it and the original native tests pass.

For example, adding Redis preserves `root` and `_apt` from the base image and
rejects a conflicting UID. The merger follows OCI layer order and whiteouts,
handles plain/gzip/xz/zstd layers, preserves capitalized and dotted account names,
and rejects non-directory account-file ancestors.

The thirteen inherited implementation patches and their integrity values, all overlays,
independent integration fixtures, six build targets and 27 tests remain unchanged.
Five account test targets bring the native AMD64 and ARM64 total to 32 each.
Full installed-image behavior remains the consumer's validation responsibility.

Native component exports retain all .sonic.13 fixes and add public headers-only interfaces, declared linker-script inputs, and producer-owned Perl CORE includes. Patch 0016 merges these changes on top of the published patch chain.

Patch 0017 adds native per-library APT targets and architecture hub aliases, retaining package-level interfaces and declared runtime dependency inputs.
