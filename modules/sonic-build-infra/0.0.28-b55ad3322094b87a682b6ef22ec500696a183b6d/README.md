# Runtime preparation, shared APT inputs and configure argument transport

This entry registers `sonic-build-infra@0.0.28-b55ad3322094b87a682b6ef22ec500696a183b6d` from the
[combined source commit](https://github.com/securely1g/sonic-build-infra/commit/b55ad3322094b87a682b6ef22ec500696a183b6d).
It preserves [source #88](https://github.com/securely1g/sonic-build-infra/pull/88)'s
original native-runtime preparation commit and closed-standard-descriptor fix,
[source #90](https://github.com/securely1g/sonic-build-infra/pull/90)'s shared APT
compatibility, and [source #91](https://github.com/securely1g/sonic-build-infra/pull/91)'s
generic helper for oversized configure linker arguments. It refreshes the one
unpublished `.28` candidate. The published `.27` entry, existing registry
overlays, and visibility patch remain unchanged.

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

The canonical catalog also declares the `libteam_deps` collection requested
by the registered libteam owner. Without that collection, #133 cannot resolve
libteam against the shared lock. This refresh preserves all 2,203 existing
package records and all 44 existing collections unchanged, and adds the
libteam collection with seven additional ARMHF package records. AMD64 and
ARM64 reuse already locked records; existing consumers keep their versions
and checksums.

## Concrete consumer examples

| Input or action | Before | After |
| --- | --- | --- |
| Buildimage #133's PI `@p4lang_pi//:sdk` configure launch with 160,581 bytes of `LDFLAGS`, including 573 library-search directories | Linux rejects `/bin/sh` with `Argument list too long` before the configure adapter can run. | The shared `configure_linker_flags.sh` helper saves the flags with shell builtins, replaces the oversized environment entry with a short file reference, then launches declared Python and configure. The existing compiler launcher preserves argument order and shortens library paths for each working directory. PI must adopt the helper in its separate recipe PR. |
| Prepare a native runtime when the caller has closed stdin, stdout or stderr | The temporary environment file can reuse descriptor 0, 1 or 2, while the preparation helper requires a private descriptor above that range. | The transport is duplicated to a descriptor at least 3 and the reused standard descriptor is closed before launching the helper; the caller's closed state is preserved. |

The linker helper must be sourced through `configure_prefix` before the first
external process. Invoking it inside the configure script is too late for this
failure. It leaves `CPPFLAGS`, `CFLAGS` and `CXXFLAGS` unchanged; its private
linker vector preserves quoted argument boundaries and rejects line breaks.
See [source #91](https://github.com/securely1g/sonic-build-infra/pull/91) and the
[failed VS job](https://github.com/securely1g/sonic-buildimage/actions/runs/42405527456/job/128508038265).
The closed-descriptor fix and its regression are in
[source commit 069604f6](https://github.com/securely1g/sonic-build-infra/commit/069604f6b578ea3692f06d38fa1606542c765887).

## Validation

The registry presubmit retains all 42 build targets and 43 test targets from
published `.27`, plus the native-preparation regression introduced by the
original `.28` candidate: 42 builds and 44 tests on native AMD64/Trixie.
The existing Libtool regression now reproduces the oversized launch failure and
checks C/C++ links from a nested directory; the native-preparation regression
also checks closed standard descriptors. Both remain part of the normal
presubmit.

The new `//apt/tests/integration:bookworm_library_import_test` runs in the source
repository's normal Bookworm phase on AMD64 and ARM64. It is not added to the
Trixie registry test list, where its platform constraint would skip it.
Bookworm import validation uses the Bookworm target platform, separately from
the Trixie registry presubmit. Source, registry-consumer and image results are
recorded in their respective PRs.
