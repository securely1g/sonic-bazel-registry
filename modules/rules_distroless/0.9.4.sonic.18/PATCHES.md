# Patch provenance for 0.9.4.sonic.18

This candidate retains the published 0.9.4.sonic.17 inputs and adds
`0022-distributed-requests.patch`: evaluated request export, root production-lock
selection, optional standalone fallback locks, compatibility-view validation,
exact distributed-request checks and optional source default architectures.
`0023-shared-linker-inputs.patch` preserves runtime and cross-package script
inputs through cc_shared_library filtering. `0024-transitive-script-libraries.patch`
represents script-referenced DSOs as native imports and rewrites their references
for the downstream _solib layout across dynamic_deps. The upstream archive and patches
0001 through 0021 remain unchanged.

The provenance of the retained patches follows.

# Distroless patch provenance and validation

`0.9.4.sonic.17` starts from published `0.9.4.sonic.16` at maintained registry
commit `47690df33f75ed36452b9fc80596cd0d599d2a5c`. It retains the exact upstream
0.9.4 archive, patches 0002–0019, existing overlays and fixtures, eight build
outputs and all 35 tests. Patch 0001 changes only the module version; new patch
0020 adds shared APT source/request/lock inputs and native package exports.
The new pkg-config relocation regression brings the selected total to 36 tests.
The target-CPU header correction described below is inherited from `.16`.

The reproduction uses the exact existing Debian linux-libc-dev 6.12.96-1
archive from FIPS registry #197. Its architecture-independent payload has
22 CPU header roots. The old AMD64 compiler command searches ARM64 first;
preprocessing those declared headers with `-nostdinc` yields `io_setup=0`
instead of 206. New native/provider tests verify both AMD64 and ARM64 without
removing any inherited crypto test or changing the runtime package payload.

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
| `0013-import-apt-lock.patch` | `0.9.4.sonic.11` | Import exact package archives and dependency graphs from one reviewed lock; include the extension's unit regressions. Origin: [build-infra #59](https://github.com/securely1g/sonic-build-infra/pull/59). |
| `0014-apt-install.patch` | `0.9.4.sonic.12` | Add optional APT/dpkg installation and original-DEB aliases that preserve locked-import repository prefixes. Installer source: [rules_distroless fork PR #2](https://github.com/securely1g/rules_distroless/pull/2), commit `b3d0573b06b682a7ae3d5de20cc8215b3be3a037`, previously proposed in closed registry #72 and reused in #110. |
| `0015-preserve-base-accounts.patch` | `0.9.4.sonic.13` | Preserve inherited OCI users and groups when adding service accounts. Source: [upstream #290](https://github.com/bazel-contrib/rules_distroless/pull/290), commit `d503c1141d3759390dc78ffbb99de33b7d4f4619`; adapted MODULE integration from [registry #128](https://github.com/securely1g/sonic-bazel-registry/pull/128). |

| `0016-native-library-exports.patch` | `0.9.4.sonic.14` | Public headers-only interfaces, declared GNU linker-script inputs and producer-owned Perl CORE includes. Source: [registry #146](https://github.com/securely1g/sonic-bazel-registry/pull/146), original commit `b10335fcfc475aa439ee4095c83315d3475d75ee`. |
| `0017-individual-apt-libraries.patch` | `0.9.4.sonic.14` | Individual `libNAME_cc`/`libNAME_shared` exports and architecture hub aliases; preserved unchanged from registry #146. |
| `0018-public-cc-import.patch` | `0.9.4.sonic.15` | Use the public rules_cc compatibility entry point on Bazel 8. Original fix: [rules_distroless #5](https://github.com/securely1g/rules_distroless/pull/5), commit `5be9ab5c921dcd58d35ccdbd81e35dd65f4a5411`; adapted to published `.sonic.14`, whose import already omits the unsupported `includes` attribute. |

| `0019-target-multiarch-headers.patch` | `0.9.4.sonic.16` | Select CPU-specific include roots in the public native header exporter; preserve declared headers and symlinks. Reproduces FIPS registry #197's AF_ALG syscall mismatch. |
| `0020-unified-apt-inputs.patch` | `0.9.4.sonic.17` | Shared APT source/request/lock inputs, native exports, declared AWK and relocatable pkg-config files; registry #207. |

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


## Public cc_import compatibility

`0018-public-cc-import.patch` changes only the generated BUILD load in
`apt/private/deb_import.bzl`. It keeps `.sonic.14`'s header propagation through
public header targets and its declared linker-script implementation. No private
rules_cc implementation is loaded by generated Debian imports. The recipe
fetches the released upstream archive and applies the local checksum-pinned
patch; the source PR above records provenance rather than an archive dependency.
Retain this patch until a selected upstream release supplies the compatible
entry point and the inherited native tests pass.


## Unified APT source and lock interfaces

Patch 0020 adds shared source/request inputs and reviewed lock imports, static-library and linker-script inputs, original archive aliases, declared AWK execution and relocatable exported pkg-config files. The package payload archives retain their original bytes. This candidate preserves patches 0002–0019 from registry PR #200 byte-for-byte, including target-CPU header selection, and retains all 35 test targets before adding the pkg-config relocation regression. The two sample package-lock tests remain in the standalone integration module. The declared AWK tool requires the gawk candidate registration.

`0021-complete-shared-package-dependencies.patch` preserves dependency expansion when a package is first selected without transitive dependencies and is later required by a native library. The shared resolution state records completed transitive work; a payload-only request cannot suppress or erase it. The Bookworm production-lock regression and native header/link tests in sonic-build-infra PR #79 cover the libc6-dev → libc6 failure.

`0025-complete-library-graphs.patch` resolves each pkg-config library separately
and represents installed libraries, symlinks, archives, object files and nested
GNU scripts as exact native dependencies. Scripts retain GROUP/AS_NEEDED
semantics and their declared file closure without being forwarded as runtime
DSOs. ELF imports use SONAME aliases and co-located implementation/interface
solib paths for clean loading. Conflicting SONAMEs fail explicitly. This patch
supersedes the basename rewriting and aggregate script imports in 0024.

`0026-relative-linker-script-inputs.patch` recognizes GNU text scripts even when
they contain no absolute paths. Relative library filenames, `-lfoo` and
`-l:filename` resolve against the script directory and then the declared package
closure, retaining shared-before-static selection. Exact resolved files are
rewritten and declared just like absolute references. Unresolved toolchain `-l`
options remain linker-controlled. The regression includes Debian ncurses-style
`INPUT(libncurses.so.6 -ltinfo)` syntax and exact-filename lookup, with real
sandboxed links and clean installed execution on AMD64 and emulated ARM64.

`0027-classify-shared-library-basenames.patch` applies shared-library suffix
matching to the filename rather than its parent directories. Configuration
paths such as `etc/ld.so.conf.d/libc.conf` stay ordinary package data and never
enter ELF inspection. Public deb/data/control interfaces keep their bytes and
metadata. The synthetic contract builds these interfaces before native targets
for a configuration-only package and a package combining configuration with
real libraries, then verifies their archives and native links on both CPUs.

`0028-isolate-native-library-analysis.patch` preserves package archive/control
imports when candidate libraries are text, opaque data or unresolved/cyclic
symlinks. Native errors are analysis-time targets selected only by the native
consumer; valid neighbors continue to link. Local symlink chains resolve to
their terminal file. Text scripts preserve original GNU syntax, comments and
layout; file operands from INPUT/GROUP/AS_NEEDED/STARTUP/INCLUDE are resolved,
including quoted paths and SEARCH_DIR inheritance into included scripts. The
GNU linker validates other commands. Exported .ld/.lds inputs support INCLUDE;
static libraries named by pkg-config can come from dependency packages. The
contract also verifies no-SONAME ELF loading through two DSO boundaries and a
relocated install. No production component build is required by these fixtures.

`0029-isolate-static-pkgconfig-variants.patch` keeps independent static-only
pkg-config interfaces out of a package's default dynamic interface when dynamic
interfaces exist. A dynamic .pc that explicitly lists both shared and static
libraries keeps all its inputs; static-only packages retain their defaults.
Explicit per-library static targets carry their own .pc flags on library-bearing
inputs. This prevents libbsd-ctor's -z nodlopen and forced constructor flags from
leaking into ordinary libbsd consumers, while explicit constructor interfaces
retain their contract. A synthetic CPython extension actually imports and returns
44 after relocating the install and hiding the build tree. The fixture also
checks explicit constructor output retains NOOPEN and ordinary DSOs exclude it.

`0030-model-pkgconfig-modules.patch` replaces patch0029's dynamic/static
classification with actual pkg-config module queries. Each module exports
`pkgconfig/<module>` and `pkgconfig/<module>/static`. Queries use only .pc metadata
from checksum-pinned DEBs in independent file-map repositories; Requires cycles
therefore create no native repository cycles. pkg-config handles Requires,
Requires.private, version predicates, variable expansion and line continuations.
Native targets carry resolved library inputs and their selected module flags;
unrelated modules do not contribute flags. Missing/version-incompatible modules
produce selected-target diagnostics while package archive interfaces remain
usable. Compatibility package targets retain their aggregate library interface
and use a matching main module's flags, with historical aggregation when no main
module is identifiable. Explicit module targets provide precise selection.

The final module implementation also preserves flags-only modules without a
physical library input, follows ordered -L lookup for compatibility targets,
and exports metadata from usr/share/pkgconfig. The fixture's flags-only module
defines an absolute linker symbol with value42; linked consumers return44 on
both architectures. The comparison against songqing-sq/sonic_rules master
(a9d618537d03f2d6da31e3a6a96d12541c361785) confirms its MODULE pins the same
Distroless commit815b4b3. Its separate linker-script generation path does not
merge all .pc link flags into libbsd; module-aware selection preserves that
ordinary-library behavior while honoring explicitly selected ctor options.

## 0031: Deduplicate resolved pkg-config dependency labels

A module's Libs and Libs.private can both reference the same installed library.
Keep the first resolved dependency label and omit later duplicates when generating
Bazel deps. Preserve link option order. The regression fixture puts the same
library in public and private linker declarations; it must analyze, link and run
through the existing two-shared-library contract. Actual Trixie libzmq3-dev
4.3.5-1+b3 provides the production static-module input.


## 0032: Preserve APT compatibility and selected module contracts

Add a generated, shared catalog of active reviewed pkg-config providers,
isolated by target architecture and dependency-connected source suites. Resolve
Requires/private through lazy, cycle-free package metadata repositories. Keep
strict module errors separate from the legacy direct-field fallback, including
metadata accepted by the former parser but rejected by SDK-required fields.
Provider headers are compilation inputs; their package-default link options
are not implicit edges of the consumer.

Native runtime edges follow selected files and ELF DT_NEEDED. Packages retain
plugins in their original archives. Ordered link arguments preserve whole-archive,
group and push/pop semantics; static/dynamic state affects exact file selection.
Search directories outrank suffix preference. Exact filenames and declared
literal archives carry their inputs. Internal targets use distinguishable names;
ambiguous public shorthand fails only on selection. Script dependency labels
are deduplicated, and usr/share/pkgconfig metadata has the ordinary file export.

The native CcInfo module supports include categories and definitions. It reports
other compiler options explicitly rather than dropping them; legacy labels keep
their former behavior and original metadata remains available. New rule-file
loads have declared bzl_library dependencies.

The fixture has 42 two-DSO chains, independent SDK/GNU controls, raw-archive
checks and negative selections. It covers the contracts above and the original
native/Python/Go/Rust boundaries. ARM64 uses target compilation and QEMU; native
host and emulated target results are reported separately. The updater's relative
MODULE/rc-path correction belongs to sonic-build-infra, not this registry patch.

## 0033-reuse-module-runtime-libraries.patch

Give each installed DSO one runtime identity across package and module contexts.
Use a shared source interface script so identical solib actions can be reused.
Preserve module-specific ordered arguments and forward their search directories
with -Xlinker. GCC otherwise copies every driver -L into COLLECT_GCC_OPTIONS;
response files do not avoid the Linux per-string environment limit.

The fixture joins 640 distinct modules sharing one DSO and checks two-level
linking plus clean installed execution. The pre-fix source fails with collect2
posix_spawn: Argument list too long on this input.

## 0034-isolate-static-private-library-dependencies.patch

Build legacy dynamic package extras from the dynamic pkg-config query only.
The union of dynamic and static query libraries incorrectly injected Libs.private
from hiredis_ssl and libxml2 into ordinary SWSS Common Python-extension links,
requiring -lssl, -lcrypto and -llzma even when those static inputs were not selected.
Explicit static module queries retain their private dependencies.

Two additional native contracts use an unavailable static-only library and
verify that both the legacy default and explicit dynamic module still link and
run. The independent whole-archive controls retain distinct dynamic and static
constructor results.

Also retain the selected unversioned link aliases as runtime-only LibraryToLink
files. configure_make collects these files into its dependency prefix and then
queries the original .pc, whose -l names require libname.so. Ordered native
selection still uses the explicit sequence and SONAME identity; the additional
aliases carry empty interfaces and do not introduce another native link choice.
The fixture reproduces this prefix collection and links/runs a plain -l consumer.

Packages with no declared headers expose empty compile-only header stubs via
cc_deb_library. These stubs add neither nonexistent usr/include search paths nor
native cc_library's implicit repository-root quote directories. Packages with
headers keep their existing header rules and paths. The previous empty-header
stubs inflated foreign configure probe commands until GCC could not spawn cc1;
iproute2 consequently recorded its real setns API as unavailable. The public
package wrappers and header-bearing _wodeps rules remain unchanged.

Legacy package defaults preserve SDK header paths as system include directories.
Explicit `pkgconfig/...` modules retain the original ordinary `-I` classification.
The contract fixture checks source-header precedence against both interfaces.

## 0035-keep-glibc-runtime-with-the-toolchain.patch

Identify the package owning the libc.so.6 ABI from ELF SONAME metadata. Keep
that package's companion DSOs out of transitive CcInfo runtime-library lists,
including package defaults, selected-module closures and foreign dependency
prefixes. The compiler toolchain and execution environment select the C runtime;
an incidental Debian dependency must not override the ELF interpreter with a
second glibc. Explicit selected library/script inputs and deb/data/control
payloads retain their files.

P4C's irgenerator reproduced a startup SIGSEGV when the Ubuntu glibc 2.43 loader
picked up Debian glibc 2.41 from its CMake dependency-prefix RUNPATH. The same
binary and input definitions succeeded with a matching 2.41 runtime. The
synthetic fixture uses an intentionally incomplete libc ABI and a companion
DSO to detect leaks, verifies both legacy and explicit dynamic consumers, and
checks that the original package archives remain complete. Its installed
consumers use the actual compiler/emulator C runtime.

## Shared prepared-lock transport (0037)

Before this change, each imported dependency set serialized the entire expanded
package catalog into its repository attributes. A 44-group, two-namespace image
graph wrote a 679 MB `MODULE.bazel.lock`, exceeding the existing 64 MiB public
evidence limit and exhausting the registry graph check's 2 GiB Java heap.

Patch 0037 keeps one prepared expanded lock in each unified extension namespace
and passes its file label to every group translator. The catalog retains expanded
roots and transitive package dependencies; the incoming raw lock cannot replace
that preparation. Resolver and independent legacy imports keep the inline API.
The translator rejects missing or ambiguous input. Published `.sonic.17` is
unchanged.

`shared_lock_archive_contract_test` runs from the independent integration module
on both architectures. It checks original archive bytes, metadata and complete
payload closures across two groups sharing the prepared lock, alongside the
unchanged legacy `archive_contract_test`.

`shared_lock_group_selection_test` adds a netbase-only group from the same
reviewed fixture and confirms that sharing the catalog does not leak the other
groups' Lua/libc closure. Its public group name occupies the first internal
catalog-name candidate, exercising collision-safe allocation.

Local validation of this prepared-lock change keeps the production policies
unchanged. The actual image consumer's lock shrank from **679,395,253 bytes to
47,094,358 bytes**. Its 89 selected modules and dependency edges (apart from the
intended Distroless version), all 88 group definitions and both 2,203-package
catalogs match the prior graph. The unchanged 64 MiB public-evidence gate passes,
as do 27 APT integration cases and 20 runtime-preparation cases. The registry
libyang consumer's 62-module graph also passes with the original 2 GiB Java heap;
its lock shrank from 679,113,658 to 46,814,311 bytes. The independent registry
fixture passes eight focused tests for AMD64 and ARM64 package selection.
These are local results; normal PR CI must pass on the newly published head.

## Declared runtime-library link search (0038)

Before this change, the native provider declared runtime DSOs and interface
files but omitted their link-time search directories. SONiC's sysrooted GCC
linker could select `libzmq.so.5` yet fail to locate its private `DT_NEEDED`
libraries: `libbsd.so.0`, `libsodium.so.23`, `libpgm-5.3.so.0`, `libnorm.so.1`
and `libgssapi_krb5.so.2`. This affected both the Rust listener test and the
C++ eventd test; adding the compiler host's native inspection tools alone
does not resolve it.

Patch 0038 attaches explicit `-rpath-link` directories to the library-bearing
inputs produced by `so_library` and the ordered `native_link_sequence`. The
source DSOs remain declared inputs, and generated SONAME symlinks are explicit
link-action inputs even when the linker otherwise consumes only an interface
file. Repeated `-Xlinker` arguments remain in an ordered list. The change adds
no direct library selection or runtime RPATH, and preserves the existing
static/dynamic link sequence and prepared-lock transport.

The separate `tests/integration/native_runtime:indirect_dependency_test`
constructs a parent DSO and two private DSOs in different directories. Two
compiler invocations consume the real direct/ordered `CcInfo` flags and link
inputs without inferred runtime search paths. The test fails to link on the
previous candidate and passes with the correction. It checks that both
executables retain only the parent as a direct fixture `DT_NEEDED` dependency,
contain no RPATH/RUNPATH, and run with eager relocation against the declared
fixture DSOs. The fixture exposes interface files as link inputs, so runtime
symlink paths must come from the provider's explicit action inputs.

## Default pkg-config header namespaces

`0039-default-pkgconfig-header-exports.patch` restricts the package-wide header
include list to the already selected `default_names`. It does not change that
selection policy, explicit module includes/defines, fallback roots, or any
library/linker behavior. This fixes ordinary libbsd headers accidentally opting
into libbsd-overlay when a foreign build stages dependency include roots.

The regression lives in the separate `tests/integration/native_headers` module,
not in an upstream test patch. Against the unchanged candidate, direct and
transitive ordinary consumers fail with recursive `stdio.h` inclusion; explicit
overlay and both fallback consumers pass. With patch0039, all five compile and
run. The same tests are added to the normal presubmit for both architectures.

## Owner-scoped archive tools

`0040-owner-scoped-archive-tools.patch` is an unreleased `.sonic.18` fix for
root-created APT repositories. The `deb_postfix` macro now resolves the existing
zstd, BSD tar and gawk labels in the Distroless module instead of forwarding
apparent names into each generated caller. Its gawk location expansion uses
the same bound label. Tool versions, archive commands, inputs and outputs are
unchanged; no root repository import or package-lock update is needed.

Origin: the Database and MACsec image analysis failure on the shared production
lock (`@zstd_toolchains` was not visible from a generated `locked_import` repo).
This SONiC-maintained adaptation is not yet submitted upstream. It follows all
39 existing patches without modifying their bytes or order. Eight pure
actual-macro/template controls cover absent and shadowed caller mappings, both
normalization branches and unchanged commands/targets. They supplement the
existing native Database/MACsec regression; no native acceptance is claimed.
