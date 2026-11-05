# Native libteam source and runtime interfaces

Register SONiC's existing native libteam build as a reusable dependency. SWSS
`teamsyncd` links both libraries and `tlm_teamd` links libteamdctl; the Teamd
image also consumes the daemon and utilities. These consumers should select
one owner rather than rebuilding libteam inside sonic-buildimage.

Upstream calls the release **1.31**. The registry's three-component format is
`1.31.0.sonic.1`; it does not change pkg-config version `1.31`, Debian source
version `1.31-1`, or the `libteam.so.5`/`libteamdctl.so.0` ABI.

| Consumer input | Before | This registration |
|---|---|---|
| SWSS `teamsyncd` needs `team_alloc` and `teamdctl_alloc` | An image-local libteam overlay must be injected | Public `@libteam//:libteam` and `:libteamdctl` C++ providers |
| SWSS installs only the two libraries | Full metadata would also advertise absent utilities | `:library_runtime_packages.json` describes exactly `libteam5` and `libteamdctl0` |
| Teamd installs daemon, utilities and libraries | Image owns their source recipe | Existing runtime/debug TAR labels and full `:runtime_packages.json` remain available |
| Exported development TAR | Generated pkg-config files can carry build-time timestamps | The accepted `/set time=0` fix preserves zero timestamps for every SDK member |

## Sources and patches

The source is the verified original `libteam_1.31.orig.tar.xz`. The separate
`libteam_1.31-1.debian.tar.xz` supplies control fields, changelog, copyright
and symbol metadata; it contains no Debian patch series. The sixteen active
SONiC patches come from the existing Make series, in the same order and with
their original filenames and authorship. [PATCHES.md](PATCHES.md) records each
purpose and immutable source. Added explanations leave every diff body intact.

The native definitions come from
[buildimage PR #161](https://github.com/securely1g/sonic-buildimage/pull/161),
with the accepted SDK timestamp fix from
[#162 at 233bde22](https://github.com/securely1g/sonic-buildimage/tree/233bde227dc62712bb3324ab4249cfbf145de893/src/libteam).
They preserve all source lists, compile/link flags, optional D-Bus/ZeroMQ
support, SONAMEs, installed modes and paths. Only the configuration-template
label moves with its owner. The original Make recipe is unchanged.

The module uses published source libnl3 and the existing shared Trixie
toolchain. Its APT selection is the existing target-library/runtime closure;
it does not create a second build-tools package set. It produces TARs and
metadata only, with no new DEB producer.

## Public outputs

- `:libteam`, `:libteamdctl`: C++ compile/link providers; corresponding
  `:libteam_shared` and `:libteamdctl_shared` targets remain public.
- `:libteam_runtime`, `:libteamdctl_runtime`, `:libteam_utils_runtime` and each
  matching `.debug_symbols` target: the existing source-owned runtime pairs.
- `:libteam_dev`: public headers, linker symlinks, pkg-config files and notices.
- `:runtime_packages.json`: all three original binary-package records.
- `:library_runtime_packages.json`: only the two library records, with the
  same control data, payload hashes, symbol metadata and required paths.

Keep library metadata paired with the two library payloads. Do not claim
`libteam-utils` is installed in an image that only consumes libraries.

## Validation scope

The ordinary `tests/consumer` module selects this entry without a source or
version override and directly selects SWSS's existing
`sonic-build-infra@0.0.26-51c838da6ff57295fde6e0bc3807841cb31a8568`.
The separate SWSS consumer checks cover its Common9 dependency. Presubmit requests native AMD64/Trixie, the nine public
TAR/metadata outputs, and three tests:

- `consumer_test` compiles and runs the existing public C consumer with the
  declared runtime closure.
- `package_test` checks the installed SDK, pkg-config/header compilation,
  native architecture and SONAMEs, all five runtime/debug build IDs and CRCs,
  isolated missing-symbol rejection, positive GDB source lookup, and the exact
  full/library-only metadata boundary.
- `sdk_timestamp_test` retains the accepted zero-time, nonzero-time, PAX
  override and empty-archive cases.

The original producer passed
[AMD64 buildimage CI](https://github.com/securely1g/sonic-buildimage/actions/runs/41960139173/job/127024306523)
at source 233bde22: installed SDK, five symbol pairs, native consumer and
no-op/config-edit/restoration acceptance. That is historical evidence for
the reused implementation, not a claim that this new registry layout has
passed native CI. The new entry currently has source-preparation and pure
validation only. Its native consumer build, downstream SWSS build and
incremental acceptance remain to be run after review. ARM rule branches are
preserved, but this proposal requests AMD64 acceptance only. Daemon networking,
LACP/kernel behavior, OCI images and the VS installer are separate checks.
