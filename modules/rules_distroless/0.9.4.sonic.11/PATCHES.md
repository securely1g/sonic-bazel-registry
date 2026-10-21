# Distroless patch provenance and validation

`0.9.4.sonic.11` applies the complete SONiC patch set to the checksum-pinned
upstream `rules_distroless` 0.9.4 archive. The locked-import extension and its integration tests are maintained in
[build-infra #59](https://github.com/securely1g/sonic-build-infra/pull/59);
this entry distributes matching bytes. The intermediate `.sonic.2`, `.sonic.3` and `.sonic.4` proposals
are not published by this change; existing published versions are unchanged.
This entry retains all `.sonic.10` behavior and adds direct runtime lock imports.

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
| `0012-headerless-includes.patch` | `0.9.4.sonic.10` | Export the package include root only when it owns declared compiler inputs; preserve all linker and transitive contexts. |

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

`0013-import-apt-lock.patch` is copied from the patch owner's
`third_party/rules_distroless/patches/0001-import-apt-lock.patch`.
`0014-locked-import-tests.patch` exposes its lazy existing-DEB fixture.
The new Starlark tests cover missing dependencies, identities, hashes,
architectures, cycles and set selection. The archive integration test checks
locked versions, independent data/control labels, architecture-independent
packages, full closures and identical contents from separate imports.
All twenty prior tests and six build targets remain selected; the four new
tests and archive output run on native AMD64 and ARM64. No test creates a DEB.
