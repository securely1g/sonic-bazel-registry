# Native library exports from APT packages

This update adds individual C/C++ library and public-header targets directly
to `0.9.4.sonic.13`, retaining that module version. It supports the native component builds in
[build-infra #67](https://github.com/securely1g/sonic-build-infra/pull/67) and
[buildimage #51](https://github.com/securely1g/sonic-buildimage/pull/51).

For example, the pinned Lua development package contains several link inputs.
A consumer that needs Lua can depend on `@registry_ci_pkgconfig//liblua5.1-0-dev:liblua5.1_cc`
to obtain that library, its headers and declared runtime dependencies without
selecting a library from the package's aggregate `CcInfo`. The corresponding
`:liblua5.1_shared` target supplies the individual link file for ordered linking.
The checked-in `registry_ci:lua_single_library_test` exercises this interface.

| Input or action | Original `.sonic.13` | Updated `.sonic.13` |
| --- | --- | --- |
| Select one Lua library from `liblua5.1-0-dev` | Package-level C/C++ interface; no public per-library target | `liblua5.1_cc` and `liblua5.1_shared` select that library |
| Compile against a development package's public headers | Consumers extract the compilation context from the aggregate interface | A public `*_headers` target supplies the headers directly |
| Use existing package-level targets or locked archive imports | Existing behavior | Preserved and tested independently |

The upstream archive and original patches `0001` through `0015` are unchanged.
Regenerated patch `0016` contains only the library-export changes relative to
the complete original `.sonic.13` source. It combines the original proposal's
`0016` and `0017`, with native linker-input handling corrected and the original
`.sonic.13` GNU linker-script bytes and remap behavior retained. This revises the
existing source recipe and exports; it adds no module version.

Native AMD64/ARM64 presubmit retains all 32 inherited tests and adds Lua
single-library, public-header and GNU linker-script coverage. The inherited
aggregate-header tests retain their original helper and assertions.
Presubmit runs 13 build targets and 41 tests on each native architecture.
Installer/account behavior below is inherited; these tests do not establish
full installed-image behavior.

## Inherited locked APT imports

Published `0.9.4.sonic.11` provides all earlier compiler fixes and `apt.import_lock` for
container package inputs. It replaces a second MODULE file repeating every
package version already recorded in the lock.

```starlark
apt = use_extension("@rules_distroless//apt:extensions.bzl", "apt")
apt.import_lock(lock = "//image:apt.lock.json")
use_repo(apt, "image_packages")  # dependency-set name in the lock
```

The extension reads the lock's exact archive URLs and SHA256 digests without
resolving package indexes or rewriting the input. Every root and transitive
package exposes independent `:data` and `:control` targets, plus its package
closure. The existing Distroless importer and archive preparation rule are reused.
Native C++ imports continue to use `apt.install`, whose Contents indexes are
not present in runtime locks.

This registry module owns the implementation, regression tests and fixture
regeneration helper. [Build-infra #59](https://github.com/securely1g/sonic-build-infra/pull/59)
is the original proposal, superseded by this registry implementation; it is not
a source dependency.
The registry runs all twenty retained tests, four locked-import regressions and
a fixture-regeneration test on native AMD64 and ARM64. The tests check graph
integrity, locked package metadata, complete dependencies,
architecture-independent packages and identical archive contents across
isolated imports. No DEBs are produced.

The archive integration test lives in the independent Bazel module at
[`tests/integration`](tests/integration). Its `MODULE.bazel` declares the
dependency and sample lock imports, and its `BUILD.bazel` exposes
`//:archive_contract_test` and `//:fixture_regeneration_test`. CI copies this
module to a fresh work directory and runs both tests alongside the twenty
retained tests and three locked-import unit tests in the registry-fetched
dependency. The test module and fixture are not
overlaid into the dependency, and no test-only patch changes its MODULE file.

See [patch provenance and validation](PATCHES.md).

## Refresh the reviewed lock fixture

Keep the Lua/netbase roots and their complete AMD64/ARM64 closures from a
reviewed image lock. From this registry checkout, run:

```sh
entry=modules/rules_distroless/0.9.4.sonic.13
python3 "$entry/tests/integration/tools/select_lock_fixture.py" \
  --input /path/to/sonic-buildimage/dockers/docker-base-trixie/bazel/apt.lock.json \
  --output "$entry/tests/integration/apt.lock.json"
```

Review the archive URLs, hashes, package versions and closure changes before
committing the updated fixture. Each package's locked SHA256 is verified when
Bazel fetches its archive. The helper only
selects existing Debian archive metadata; it does not produce DEBs or resolve
new packages. Passing the checked-in fixture as `--input` regenerates identical
bytes. The ordinary Bazel `fixture_regeneration_test` invokes that helper with
declared inputs and writes its comparison copy to a temporary test directory.

The shared registry runner validates every module through the same CI entry
point. It checks the native Linux host and Debian userspace architecture and
verifies that recipe inputs remain unchanged, including after a failed build.
It retains the generated lock, input declarations, source hashes and uncached
test results. Both native jobs must execute all 41 selected tests, including the 32 inherited
checks, the Lua single-library test and eight additional header/linker-script
checks. Cross inspection
of ARM64 archives on AMD64 is not native ARM64 execution.

## Preserve the base image's users and groups

[Registry #110](https://github.com/securely1g/sonic-bazel-registry/pull/110)
published `.sonic.12` on maintained `main`. Published `.sonic.13` extended it
with account preservation while retaining the installer and earlier tests. This
update retains that implementation and the public
`accounts(base, architecture, users, groups)` API used by
[build-infra #57](https://github.com/securely1g/sonic-build-infra/pull/57).

For example, adding a Redis user and group to a base containing `root` and `_apt`
keeps both existing accounts. A conflicting Redis UID fails the build instead
of replacing an inherited record. The rule follows OCI layer order and deletions,
handles plain, gzip, xz and zstd layers, and emits an account layer and a receipt.
It reuses the existing account writers, declared Python tools and BSD tar.

`0015-preserve-base-accounts.patch` carries the reviewed implementation from
[registry #128](https://github.com/securely1g/sonic-bazel-registry/pull/128) and
[upstream #290](https://github.com/bazel-contrib/rules_distroless/pull/290).
Those links record implementation provenance; the recipe fetches the upstream
0.9.4 release and applies local patches. The generic implementation and tests
match upstream proposal `d503c1141d3759390dc78ffbb99de33b7d4f4619`.
Only its MODULE integration adapts the installer's existing Python dependency:
`rules_python@1.7.0` and Python 3.11 are declared while `tar.bzl@0.10.4` stays in place.
Keep this patch until an upstream release supplies the feature and passes the
same validation.

Both native architectures run five added account targets: unit cases and plain,
gzip, xz and zstd OCI layer tests. They include inherited names such as
`Debian-exim` and `monitor.agent`, and reject an upper-layer `/etc` symlink
rather than incorrectly exposing hidden lower-layer accounts. All 27 existing
tests remain selected, including independent lock fixture regeneration.

Patch `0016` adds native library exports, public headers, declared linker-script
inputs and producer-owned Perl CORE includes above the published patch chain.

Individual shared libraries are exported as `libNAME_cc` and single-file `libNAME_shared` targets under each owning development package. Consumers can use specific libraries without selecting from a package-level CcInfo in private adapters.

GNU linker scripts keep their original installation-path references. The package
exports the exact referenced files and remap flags on its library-bearing
`CcInfo` input, so native `cc_shared_library` retains them in its link action.
This preserves the existing script format used by configure-based consumers.

A pre-existing limitation remains for GNU scripts through native
`cc_shared_library(dynamic_deps=...)`: Bazel 8.5.1 forwards the precompiled
libraries but drops their remap flags and additional inputs. The existing
Debian CI base contains the exact `libbsd.so.0.12.2` file used by SWSS Common;
a local Ubuntu host without that file cannot complete the same downstream
link. The direct-link regression does not establish hermetic linking through
that boundary. This update preserves the published behavior and does not
change that separate contract.

The new public header targets are opt-in: existing aggregate package targets
retain their original dependency shape and include paths. Attaching every new
header target to those existing aggregates expanded FIPS OpenSSH's compiler
arguments enough to produce `posix_spawn: Argument list too long`. Keeping the
old aggregate interface avoids that growth while individual library consumers
can use the new headers explicitly.
