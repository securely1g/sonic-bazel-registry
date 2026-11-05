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

The ordinary `tests/consumer` module requests this entry without a source or
version override and requests the production module's existing landed minimum,
`sonic-build-infra@0.0.25-3ee15ec9b4d99d7f8eae3e324cead79b203b451e`.
This removes only the standalone test root's explicit `.26-51c838da` request;
the separate SWSS/Common9 consumers retain their own dependency requests.
The actual resolved graph must confirm the `.25` selection before acceptance.
Presubmit still requests native AMD64/Trixie, the nine public
TAR/metadata outputs, and four tests:

- `consumer_test` compiles and runs the existing public C consumer with the
  declared runtime closure.
- `package_test` checks the installed SDK, pkg-config/header compilation,
  native architecture and SONAMEs, all five runtime/debug build IDs and CRCs,
  isolated missing-symbol rejection, positive GDB source lookup, and the exact
  full/library-only metadata boundary.
- `sdk_timestamp_test` retains the accepted zero-time, nonzero-time, PAX
  override and empty-archive cases.
- `verify_rebuild_test` records simulated Bazel commands to check the incremental
  driver's input selection, flags, output/evidence checks and restoration on
  failure. It never launches Bazel or compiles a native fixture.

Consumers run the exported `@libteam//:bazel/verify_rebuild.py` source using their
existing Bazel entry point: `python3 <selected-script> --bazel <entry-point>
--bazel-arg=<flag> --output artifacts/rebuild`. Repeat `--bazel-arg` to preserve
platform, downloader and cache settings. Resolve the script with that same
entry point's `cquery --output=files`. With the pinned Bazel 8.5.1, Bzlmod and
standard local filesystem, obtain `info output_base` and validate its
`execroot/_main` directory; this avoids `info execution_root` constructing a
configuration before apparent platform labels are mapped. Keep all caller
options and do not copy the script into the consumer. The driver checks that it is the selected owner
script, hashes the owner's MODULE/BUILD/config/script, and records four builds:
baseline, no-op, a `PACKAGE_VERSION` input edit, and exact restoration. All nine
outputs must reproduce on no-op/restoration. The edit must change the utilities
TAR while leaving the libraries, SDK and library-only metadata unchanged.
`rebuild.json` includes each output hash, four successful BEP files and the
commands/flags. Observed registry lock lookups may include historical entries;
pair them with the consumer's effective-registry receipt. This proves output
equality and input invalidation in one output base, not zero executed actions,
fresh-cache behavior or remote cache hits. Native execution of the owner
probe under the changed standalone consumer remains a remote CI acceptance gate.

The original producer passed
[AMD64 buildimage CI](https://github.com/securely1g/sonic-buildimage/actions/runs/41960139173/job/127024306523)
at source 233bde22: installed SDK, five symbol pairs, native consumer and
no-op/config-edit/restoration acceptance. The registry owner at `4ed05183`
also passed its nine outputs, four tests and exported incremental probe in
[worker CI](https://github.com/securely1g/sonic-buildimage/actions/runs/42036039738/job/127274358819).
Those results retain their original dependency graphs. The changed `.25`
standalone consumer still needs actual resolution, the same native outputs/tests
and incremental acceptance; static API comparisons do not transfer that proof.
Downstream SWSS validation remains separate. ARM rule branches are
preserved, but this proposal requests AMD64 acceptance only. Daemon networking,
LACP/kernel behavior, OCI images and the VS installer are separate checks.
