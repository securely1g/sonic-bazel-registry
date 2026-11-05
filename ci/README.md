# Registry CI

Registry CI validates a module as a dependency in a fresh Bazel consumer. It
resolves the module from the proposed registry checkout, then builds the declared
outputs and runs explicit consumer and package tests. This exercises registry
resolution, archive integrity, patch and overlay application, compilation, and
the behavior covered by each module's tests.

The workflow runs on every pull request, pushes to `main`, and manual dispatches.
Pull requests select affected module versions. Changes to the CI implementation
or workflow also test the latest version of each module covered by CI. Pushes and
manual runs test those latest versions by default. To test every configured
historical version, select **all_versions** when manually running the workflow,
or use `plan --all` locally.
Revised unreleased candidates require a validation configuration too.
Published consumer inputs and version directories cannot be removed or rewritten;
standalone documentation and test maintenance is allowed as described below.
Unchanged historical entries without a configuration are not represented as
validated. Documentation-only changes can produce an empty module matrix.
In particular, `modules/<name>/README.md` and permitted documentation-only edits
inside a published version do not select a version. Documentation changes in an
unpublished candidate still validate that candidate.

`Registry CI` is the stable aggregate check intended for branch protection. It
passes only when planning and the runner's unit tests pass, and every selected
module job passes. A skipped module matrix is accepted only after successful
planning explicitly selected no jobs. Adding the workflow does not itself change
repository branch-protection settings.

## Verified source mirrors

The runner passes Bazel's standard `--experimental_downloader_config` with
[`source_mirrors.cfg`](source_mirrors.cfg) to dependency preparation, builds,
tests and output queries. One rewrite is the exact upstream URL for
BCR `pigz@2.8.bcr.2`, used by build-infra's reproducible gzip tool when packaging
WPA's debug TAR. The original URL now serves different bytes; a clean
[WPA registry build](https://github.com/securely1g/sonic-bazel-registry/actions/runs/41587703074/job/125760920377)
fails its BCR checksum before compiling any source.

The MacPorts mirror retains the original archive with SHA256
`eb872b4f0e1f0ebe59c9f7bd8c506c4204893ba6a8492de31df416f0d5170fd0`.
Bazel still verifies BCR's unchanged integrity and applies its unchanged patches.
Other pigz versions and paths are not rewritten. No source/version override,
custom pigz module, prebuilt pigz, or disabled integrity check is involved.

Debian snapshot downloads retain `snapshot-cloudflare.debian.org` and the
original `snapshot.debian.org` URL as fallbacks. Pinned binary packages first
try the official Debian pool and, for the verified historical inputs below,
an exact content URL. This preserves the complete path,
including the snapshot date, for ordinary and security archives and indexes.
Registry validation encountered HTTP 503 responses from the original endpoint
while fetching pinned libpcap and libc debug packages, before source compilation.
Both download attempts remain subject to the original locked SHA256.
No package version, snapshot date or checksum changes.

This config applies automatically in this registry's validation runner. It does
not change how standalone consumers download dependencies. Until BCR's upstream
source location is repaired, standalone callers can opt in using an absolute
path to a checkout of this config:

```sh
bazel build --experimental_downloader_config=/path/to/sonic-bazel-registry/ci/source_mirrors.cfg //your:target
```

The real Bazel runner tests fetch BCR's pigz into a new, empty repository cache
without a distdir, verify its original archive hash and patched MODULE, and
confirm that a mirror serving different bytes is still rejected. These are
repository fetches; they execute no compilation or package actions.

Controlled snapshot endpoint tests also use real Bazel with empty caches to
verify ordinary/security archive and index routing, original-URL fallback,
and rejection of incorrect bytes. These fixtures test downloader behavior;
they do not establish availability of an external mirror.

The native AMD64/ARM64 runner tests retain these source-fetch checks. The old
pigz branch has no exception. The temporary Debian-transport branch exception
below preserves the publication-policy plan and runner/fetch suites; all other
branches retain normal module selection.

## Pinned Debian package downloads

The downloader tries official Debian pools before the maintained Cloudflare
mirror and original Snapshot fallback for pinned binary packages. Two pool
match rules reuse [buildimage PR181](https://github.com/securely1g/sonic-buildimage/pull/181).
Exact historical content routes add alternatives for the verified inputs below.
The pool/content rules do not match indexes or source archives; those keep
main's Cloudflare/original routing. Pigz, package versions and hashes stay intact.

For example, [BMv2 PR211](https://github.com/securely1g/sonic-bazel-registry/pull/211)
failed during AMD64 analysis while fetching the declared ARMHF
`libthrift-dev_0.19.0-4+b1_armhf.deb` (SHA256
`feef88038da4c689aa4e46f4bf2d39c90b7d4971c0ae5ab0f9568fa671b1d4c3`).
Its APT hub reads compiler metadata for all declared architectures before
selecting native targets; this request does not imply ARMHF compilation.

| Input or action | Before | After |
| --- | --- | --- |
| The pinned BMv2 libthrift package | Cloudflare mirror, then dated Snapshot | Official pool, then the same two fallbacks; unchanged SHA256 required |
| `debian-security` binary package | Cloudflare mirror, then dated security Snapshot | Official security pool first, preserving `pool/updates` and both fallbacks |
| Package mirror serves different bytes | Checksum failure | Checksum failure |
| Dated package index or source archive | Cloudflare mirror, then original URL | Same two routes |
| Existing pigz source | Verified MacPorts mirror | Same verified MacPorts mirror |

The historical failures below describe the configurations at their linked runs.
This addresses the same transport failure affecting
[build-infra registration226](https://github.com/securely1g/sonic-bazel-registry/pull/226)
and the declared tools in
[source PR82](https://github.com/securely1g/sonic-build-infra/pull/82).
The registry runner already passes this config to all preparation, build, test
and output-query commands. Standalone source CI ignores dependency RC files;
it needs a separate explicit opt-in to an immutable, checksum-verified copy of
this combined config. This change does not update those PR heads or imply their
native checks have passed.

Historical packages can disappear from the current official pool. Four exact
AMD64 payloads already used by the source-image worker have verified Snapshot
content-ID routes: `libpython3.13-minimal`, `libpython3.13`, `libdebconfclient0`
and `libselinux1`. These routes follow the official pool and precede the dated
Cloudflare/original fallbacks. Each matches one timestamp, version, architecture and path;
the declared package SHA256 still verifies the bytes. The existing Bookworm
security-header content route is retained.

[Source PR83's AMD64 run](https://github.com/securely1g/sonic-build-infra/actions/runs/41909259565/job/126852139994)
built all 15 tools and passed its initial 12 tests, then failed analysis for a
fresh three-test run: the selected `libpython3.13-minimal` returned 404 from the
pool and 503 from its dated Snapshot URL. The content-ID route reuses the same
locked bytes. Other historical packages still depend on an available download
route; this does not repair snapshot index outages or change package selection.

The same ordered fallback covers three more exact historical payloads:
`libheif1_1.19.8-1_amd64.deb`, selected through Graphviz by
[libteam's AMD64 retry](https://github.com/securely1g/sonic-buildimage/actions/runs/41900723985/job/126883238634).
Its pool returned 404 and its dated Snapshot URL returned 503 during analysis.
The existing 520,256-byte package matches the same URL's retained source-CI
recipe and SHA256 `06460065e7768d7a4a72cb02a0eddd386936756a33596bb23901faeb72dc8f68`.
The libteam artifact did not retain its generated lock; this is not a claim
that its missing lock was inspected. No package version changes.

FRR's inherited image checks failed on
[`libaudit-dev_4.0.2-2+b2_amd64.deb`](https://github.com/securely1g/sonic-buildimage/actions/runs/41900888844/job/126822668186)
and [`uuid-dev_2.41-5_amd64.deb`](https://github.com/securely1g/sonic-buildimage/actions/runs/41900888825/job/126822668789)
with the same pool-404/Snapshot-503 sequence. Their exact content-ID routes use
the existing 89,348-byte and 48,836-byte packages, independently checked against
the matching immutable source-image recipes. The failed-run FRR generated locks
were not used for this binding; the matching source-image recipes supply the
integrity proof. Both packages are AMD64, including the execution
dependency used by the ARM64 image check. These routes do not change the
requested package versions, architectures or integrity checks.

[FRR's YANG AMD64 check](https://github.com/securely1g/sonic-buildimage/actions/runs/41931851590/job/126930441231)
also stopped during its initial image-root query on
`libc6-dev_2.41-12+deb13u3_amd64.deb`: pool 404, then dated Snapshot 503.
Its exact content route retains SHA256
`53a9b789bb02415d758f652ef5ac913d89fed29782610e9fe0fd2488e4f2e465`.
The 1,992,332-byte payload matches the generated lock from the successful native
FRR job at the same source `7cf59340` and catalog `cfd42fb5`; the failed YANG
job's lock was not used. YANG's initial query used only the generic shared
default, so that workflow needs its own verified opt-in to this configuration.

[FRR's Eventd AMD64 check](https://github.com/securely1g/sonic-buildimage/actions/runs/41942880383/job/126967800467)
failed its initial action query on `linux-libc-dev_6.12.96-1_all.deb`, after
the official security pool returned 404 and the dated Snapshot URL returned 503.
Its exact [content URL](https://snapshot.debian.org/file/66b33fe93d5d572e06cdabdd49d01c7b4947cfc7)
returned the same 2,859,420 bytes with SHA256
`c514b81492fc01c573ecfc809f9b460023d50e5006848c4caf78997bf1f776a5`.
The payload matches the existing cache and accepted FRR native lock; the failed
Eventd job did not retain a lock. Only this dated package URL gains a content
fallback between its official pool and original Snapshot URL. Package selection
and checksum verification stay unchanged; consumers must explicitly update their
immutable config pin before using the route.

[Libteam's AMD64 native check](https://github.com/securely1g/sonic-buildimage/actions/runs/41946663549/job/126980465955)
also failed during analysis on Graphviz's `libmount1_2.41-5_amd64.deb`
dependency: pool 404, then dated Snapshot 504. Its exact
[content URL](https://snapshot.debian.org/file/a82622f9dbedc5d438d8791f4e3a59f6f9976d88)
returned 208,788 bytes matching SHA256
`cd9efc7addd2556062f6d148b502e38a64e08c0ab220806219cfffd865f0f6f6`
and the existing cache. The accepted `78a2189c` native lock binds that package;
its source and APT inputs are unchanged at failed head `4b610cf6`. This is not
a failed-run lock claim. The route is limited to that exact AMD64 package URL
and preserves the original checksum, pool-first order and dated fallback.

[FRR's OCI AMD64 check](https://github.com/securely1g/sonic-buildimage/actions/runs/41942880224/job/126967800025)
failed during Sysmgr image analysis on the inherited base-image input
`jq_1.7.1-6+deb13u2_amd64.deb`, after pool 404 and dated Snapshot 503.
Its exact [content URL](https://snapshot.debian.org/file/5556211154d1adb33a69780c9b9385f7cf79fda9)
returned 77,760 bytes with SHA256
`c6464bdc20086222fa9295481367e9a52f3fb78120a14089bae5f0d36f1b8a74`,
matching the existing cache and checked-in base APT lock. The accepted FRR
`7cf59340` generated recipe has the same URL and checksum; the relevant package
and workflow inputs are unchanged at failed head `ce01ca5f`. The failed OCI
generated lock was not used. This exact package gains a content fallback;
other package versions, architectures and dates retain their existing routes.

[MACsec's AMD64 check](https://github.com/securely1g/sonic-buildimage/actions/runs/41940005503/job/126958076273)
failed its initial action query on the declared `gzip_1.13-1_amd64.deb` build
tool: pool 404, then dated Snapshot 503. Its exact
[content URL](https://snapshot.debian.org/file/17e2275e726dad554ab38aa3f3d240f5270923cb)
returned 138,408 bytes with SHA256
`c98b1130f08ef6ac3932972c56be84cfc308ce1afa37105cb06aaf47ced2d078`,
matching the existing cache and a retained source-image recipe for the same
dated URL. The failed MACsec generated lock was not used for this binding;
its selected immutable infra recipe declares the same package and snapshot. Only that exact
AMD64 URL gains a content fallback between the pool and dated Snapshot URL.
Package selection, hashes and other URLs remain unchanged; consumers must opt
in to the updated immutable config before using this route.

MACsec's other AMD64 checks failed on the exact locked `libc6` version
`2.41-12+deb13u3`: [SWSS](https://github.com/securely1g/sonic-buildimage/actions/runs/41940005660/job/126958076493)
requested the AMD64 package, while
[OCI](https://github.com/securely1g/sonic-buildimage/actions/runs/41940005578/job/126958077370)
and [libteam](https://github.com/securely1g/sonic-buildimage/actions/runs/41940005648/job/126958076632)
requested the ARM64 record during multiarch sysroot analysis. These were AMD64
jobs, not ARM64 compilation. Both requests reached a failing dated Snapshot
after the official pool. The two exact content URLs returned the locked bytes:

- AMD64: 2,849,576 bytes, SHA256
  `8ffd13165b9ee3f067e2ee670df718e48c1bdaa18676ac93d1de761dbbb3913c`.
- ARM64 analysis input: 2,489,480 bytes, SHA256
  `ff529924782d3286181188fc265a6a92e7fe28975fb3a925dc0e05c0ca66e52f`.

Both payloads match the checked-in base APT lock at failed source `e9cfdb54`
and the existing cache. The additional routes match only that date, version,
architecture and path; they do not select new packages or run ARM64 targets.

[MACsec's native libteam AMD64 check](https://github.com/securely1g/sonic-buildimage/actions/runs/41958919046/job/127020338914)
then failed on `ss-dev`'s `libss2_1.47.2-3+b11_amd64.deb` dependency:
pool 404, followed by dated Snapshot 503. It already used config `27b16008`;
this exact package needs an additional fallback. The official
[content URL](https://snapshot.debian.org/file/458f436ed67e7f80aed736c6665c6b725301024c)
returned 29,740 bytes matching SHA256
`879e8477dc20006e59788831e4f3a436d15afe3c055ae0e93beb96696f0e5eb1`
and the existing cache. The retained AMD64 Packages index and generated recipe
from accepted libteam source `78a2189c` bind that checksum to the same immutable
Snapshot selected by failed source `d2bd7e18`; the failed job's generated lock
was not used. The route adds only this content URL between the existing pool
and dated fallback. Other versions, architectures and dates retain their routes;
package checksums and source inputs remain unchanged.

[MACsec's shared SWSS AMD64 check](https://github.com/securely1g/sonic-buildimage/actions/runs/41970601688/job/127057690672)
then failed before compilation on Graphviz's
`libheif-plugin-dav1d_1.19.8-1_amd64.deb` dependency: pool 404, followed by
dated Snapshot 503. Config `cecadbe6` already covered `libheif1`, but not this
separate plugin. Its official
[content URL](https://snapshot.debian.org/file/4db82883543536a32eb80350a3ac4149d85009de)
returned the same 11,688 bytes as the existing cache, with SHA256
`fed7de7d14f7df765bb6ef1a79bd55b90475808793a5c41dc9ccb9deacf639ae`.
The retained libteam `78a2189c` generated recipe and immutable AMD64 Packages
index bind the same dated package selected by failed source `eea299b0`; this
is not a claim about the failed job's generated lock. The exact AMD64 mapping
adds this content URL between the existing pool and dated fallback, preserving
package selection, checksums and other routes. A bounded check from this
workspace could not establish Cloudflare availability for this plugin or
`libss2`: each TLS connection timed out once, without an HTTP response. This
does not establish a permanent endpoint failure; both maintained generic
routes remain enabled.

[FRR's native AMD64 check](https://github.com/securely1g/sonic-buildimage/actions/runs/42051339153/job/127327932746)
and [later Sysmgr analysis in its OCI check](https://github.com/securely1g/sonic-buildimage/actions/runs/42051339203/job/127327935067)
failed on `libpython3.13-stdlib_3.13.5-2+deb13u4_amd64.deb` after trying the
pool and dated Snapshot. [Eventd's AMD64 check](https://github.com/securely1g/sonic-buildimage/actions/runs/42051339451/job/127327933410)
failed similarly on `perl_5.40.1-6_amd64.deb`. The OCI archive build and its
12 tests had already passed; its later failure does not invalidate that result.
Each exact official content URL returned HTTP200 and bytes matching the accepted
`c589d2e5` lock and existing cache:

- [Python stdlib](https://snapshot.debian.org/file/34446b6d753038d30cc9dfb5bf17987ff56071da):
  1,957,100 bytes, SHA256 `0def2d972310b59704ad119abee5a97f95409e14ff1359edd8cc7b8892cfd43f`.
- [Perl](https://snapshot.debian.org/file/9c5005df956b8fa8a3f487c175499e6029669465):
  267,336 bytes, SHA256 `11ec93d44649e9b37e3bddcf32a5f01d6e9dd3d0d79aac621b49473539c8f5b8`.

The failed `f750ee5c` source retains the accepted module and download inputs;
its generated lock was not used for this binding. The SHA1 in each content URL
locates the payload; Bazel still enforces the original SHA256. These two exact
AMD64 URLs gain the content route after the pool and before the unchanged
Cloudflare/original fallbacks. The separate Cloudflare probes timed out during
TLS from this workspace, which does not establish a permanent mirror failure.
Standalone consumers still need an explicit immutable-config update; these
successful payload requests are not new native acceptance.

The exact owned `codex/registry-debian-pool-transport` branch retains the full
publication-policy plan and AMD64/ARM64 runner suites, including real checksum
rejection and cold-fetch tests, while selecting no unrelated module jobs.
Unexpected files fail this exception; other branches and pushes retain normal
selection. The branch exception remains a Draft readiness limitation and must
be removed before Ready. The real download tests only fetch existing payloads
and execute no package producer or compilation.

## Kernel build-tool cache downloads

The runner starts each consumer with `--ignore_all_rc_files`, so it explicitly
passes the same download policy as the source repositories:

```text
--remote_download_regex=(^|.*/)tools/build_tools/kernel_runtime_(amd64|arm64)(/.*)?$
```

This applies to build, test and output-query commands for both native
architectures, including checked-in integration test modules. It downloads the
kernel build-tool tree before local actions use its directory symlinks. For
example, sairedis' generated Debian metadata uses those tools; restoring the
cached tree without this policy can leave its Perl `5.40/machine` alias missing.
[The native cache experiment](https://github.com/securely1g/sonic-build-infra/actions/runs/40080628232)
reproduced that failure and verified the targeted flag on AMD64 and ARM64.
Other output trees keep Bazel's normal download policy. Read-only `info` path
queries do not need the flag.

## How CI selects the latest version

Routine CI compares the numeric release, then the SONiC patch revision. For
example, `0.9.4.sonic.10` is newer than `0.9.4.sonic.9`, and `0.9.5.sonic.1`
is newer than both. Existing `-sonic.N` spellings remain supported; the dotted
spelling wins when the release and patch revision match.

For source versions with the same numeric release and SONiC patch, the last
registration in `metadata.json` wins. This includes the published Go snapshot
form, such as `0.0.0.sonic.1-20200309174518-a00bece872fc`. Git hashes do not indicate which commit is newer. Append
new registrations without reordering existing entries. A later append of an
older release cannot displace a higher release: build-infra `0.0.18-95cd3a9...`
is selected ahead of any `0.0.8-...` registration. This is a CI selection rule,
not a change to Bazel's dependency resolution.

Latest selection skips versions listed in `yanked_versions`; a module with all
versions yanked contributes no routine jobs and is reported in the plan log.
Modules with no `presubmit.json` at any version remain outside CI coverage.
For a module already covered by CI, the latest non-yanked version must have a
configuration: planning fails instead of silently testing an older version.

A PR that revises an unreleased `modules/sonic-build-infra/0.0.8-.../` candidate
still tests that exact version. Maintaining a published version's standalone
tests or `presubmit.json` also tests that exact version, even when it is historical.
Disallowed published input changes are rejected before selecting jobs.
If it also changes CI, the plan includes both the edited version and the latest
version, once each. Module metadata changes retain their existing
coverage: an append-only release addition tests the added versions; other
metadata edits test every listed version. Explicit `plan --all` includes every
version with a configuration, including historical or yanked versions, without
replacing one with another.

Latest selection only changes which standalone module jobs run. Each selected
version keeps its declared architectures, targets and `consumer_deps` pins;
older versions remain available to consumers and can still be tested explicitly.
Routine CI does not claim that all historical versions passed.

## Publication policy checks

Before selecting module jobs, the planner checks that each affected module has
at most one version absent from the maintained `main` branch. Published consumer
inputs must remain identical, and metadata must list every version directory.
This also checks inherited candidates when a PR changes only
metadata or documentation; the actual stacked PR base is used only to select
validation jobs.

For supported archive entries, the only mutable entry-relative paths are regular
files at `README.md`, `PATCHES.md`, `docs/**`, `presubmit.json` and `tests/**`.
These may be added, edited or removed, and regular maintenance files may change
their executable bit. All other paths are protected by their Git object type,
mode and contents. This includes `MODULE.bazel`, `source.json` and every file
under `patches/` or `overlay/`, even if its name looks like documentation or a
test. Symlinks and submodules are never maintenance files. Source layouts or
recipe fields not understood by this policy retain whole-entry immutability.

The unchanged source recipe takes precedence over the maintenance allowlist:
the checker protects a local file named by its source fields, including archive
or mirror URLs with that relative path. URL escaping and dot components are
normalized before comparison. This check is intentionally conservative, so an
unrelated fetch URL with the same path suffix also protects the local file.
The informational `docs_url` field is excluded from this reference check;
`source.json` itself remains immutable. The checker does not try to infer that
an unknown file or source layout is safe to change.

Permitted published documentation changes select no module jobs on their own,
so historical entries need no new `presubmit.json` merely to fix their README.
Standalone test or CI-manifest changes select the exact affected version and
must pass its configured native tests. Shared CI changes retain their ordinary
latest-version matrix. No source payload changes or weakened test assertions
are implied by a maintenance exception; ordinary review still applies.

For example, with `libyang-python@3.1.0.sonic.2` on `main`, a parent adding
`.sonic.3` and a child adding `.sonic.4` fail with two unreleased candidates.
After `.sonic.3` reaches `main`, preserving its consumer inputs and adding
`.sonic.4` passes. Updating `.sonic.3`'s standalone tests instead uses its existing
version. Unchanged historical releases do not require new CI manifests.

For PRs and manual runs, the workflow explicitly fetches the public maintained
repository's `main` and records its SHA in `plan.log`. It does not trust a fork's
branch or treat a stacked PR base as publication. For pushes to `main`, the
publication baseline is the event's **pre-push** `before` SHA; using current
`main` would compare the push against itself. Pushes also pass `--push` to
compare directly against that baseline, detecting non-fast-forward rollbacks
that remove published entries. Missing or unavailable baselines
fail planning, including in `--latest` and `--all` modes.

Affected modules are those changed from the common ancestor of that publication
baseline and the checked-out head. Releases in unrelated modules after a branch
fork do not count as deletions. If a touched module has since published a new
version, rebase to retain its published entries. Protected file comparisons
include contents, modes, additions, deletions and type changes.

CI sees the checked-out stack, not independent open registry PRs or downstream
repositories. Authors must also audit those PRs and update affected consumer
versions, registry revisions, overrides, and lockfiles when consolidating a
candidate. This policy does not change native module validation coverage.

## Module configuration

Add `modules/<name>/<version>/presubmit.json` with the module's registry change.
Each module registration or update belongs in its own PR, including its
configuration and tests. The initial example is
[`libyang 3.12.2.sonic.1`](../modules/libyang/3.12.2.sonic.1/presubmit.json).
The initial validator supports HTTPS source archives with integrity hashes and
optional patches and overlays. Other registry source types need explicit runner
support before onboarding.

The configuration declares:

- `architectures`: native execution and target architectures to validate,
  currently `amd64` and/or `arm64`.
- `consumer_deps`: additional direct dependencies required by the test consumer,
  each with `name`, an exact `version` to test, and optional `repo_name`. CI pins
  every entry to its declared version using `single_version_override`; no
  separate pin flag or override map is needed. Use the module's `name` for
  selection; `repo_name` only controls its apparent repository name in targets.
- `platforms`: an explicit Bazel target platform label for each architecture.
- `host_platforms` (optional): an explicit Bazel host platform label for every
  architecture in `architectures`. This selects the default execution platform
  used to compile tools such as a source-built P4 compiler. A Trixie target
  platform alone does not select the Trixie toolchain for execution dependencies.
  For those consumers, map each architecture to its native Trixie platform,
  matching `platforms`. The runner passes the choice to build, test and info
  commands and records `platform` and `host_platform` in `validation.json`.
  Omitting the map preserves Bazel's existing host-platform default and records
  `host_platform: null`; no host flag is added to other modules.
- `build_targets`: required output labels, including runtime and matching debug
  packages where the module provides them.
- `test_targets`: explicit consumer and package test labels.
- `integration_test_module` (optional): an entry-relative directory containing a
  separate test module, for example `tests/integration`. CI copies its ordinary
  `MODULE.bazel`, `BUILD.bazel`, tests and fixtures into the fresh consumer. The
  test module must directly select the tested module's exact name and version;
  it cannot use source overrides or include other MODULE files. Keep
  `consumer_deps` empty and omit the generated Go/Rust options in this mode:
  the checked-in test module owns its dependencies and toolchains. Explicit
  root targets such as `//:archive_contract_test` are then allowed alongside
  `@<module>//...` targets. Omitting this field keeps the generated consumer.
- `test_runtime_preparation` (optional): reuse the tested source's Python helper
  to prepare runtime libraries in the disposable native test container. Set
  `script` to its path relative to the fetched source and `sha256` to the exact
  file digest. For example, Common's C++ and Rust tests need `libhiredis.so.1.1.0`
  at execution time; its existing helper installs missing runtime packages from
  the resolved Debian snapshot without changing the compiler or built library.
  No module opts in implicitly, and the registration must review the helper's
  package selection and installation behavior together with its checksum.
- `generated_module_overlay` (optional): set to `true` to derive
  `overlay/MODULE.bazel` from the maintained registry `MODULE.bazel`, as described
  below. Any other value is rejected. Omit the field for existing entries that
  maintain their source module through other overlays or patches.
- `go_sdk` (optional): select the consuming root's Go SDK with an exact stable
  version, for example `{"version": "1.25.0"}`. Declare `rules_go` in
  `consumer_deps` unless it is the tested module. The runner uses that
  dependency's apparent `repo_name` to call its `go_sdk` extension and download
  the selected version. This supplies the ordinary root SDK declaration that a
  dependency's `dev_dependency` extension cannot provide. Omitting this field
  preserves rules_go's default SDK selection. The generated declaration and
  `validation.json` record the choice; build and test coverage is unchanged.
- `build_flags` (optional): module-qualified Starlark settings applied to both
  builds and tests, for example
  `--@sonic-swss-common//tools/bazel:yang_modules=False`. Each setting must belong to
  the module under test and include its value. Native Bazel options, duplicate
  settings, and options that redirect registries or override test execution are
  rejected. The selected flags are retained in `validation.json`.
- `rust_toolchain` (optional): declare the consuming root's Rust toolchain with
  an exact stable version, for example `{"version": "1.90.0"}`. Declare `rules_rs`
  in `consumer_deps` unless it is the tested module. The runner calls its
  reexported `rust` extension using the declared apparent repository name and
  registers the pinned toolchain for native AMD64 and ARM64. This supplies the
  root declaration required by `rules_rs` 0.1.0 when testing a Rust module as a
  dependency, matching Common and SWSS. Omitting it preserves other consumers.
  The generated declaration and `validation.json` retain the selection.
  Set optional boolean `mangled_allocator_libraries` to `true` for Rust targets
  linked by the C++ toolchain with the allocator shim used by Common and SWSS.
  Set optional boolean `bindgen` to `true` when the consumer needs the
  `rules_rs` binding-generator toolchain. Both default to `false`; the runner
  imports and registers only explicitly requested support.
- `rust_preparation` (optional): prepare one shared Rust dependency module before
  building its targets. Set `module` and its apparent `repo_name` to either the
  tested module or a declared `consumer_deps` entry. Pin `helper_revision` to a
  full `sonic-build-infra` source commit and `helper_sha256` to that revision's
  `tools/rust/prepare.py` file. CI verifies the helper, fetches the declared module
  through this registry, and prepares a private copy. For example, this lets the
  Serde round-trip test use generated Rust dependency metadata without committing
  that metadata in the source archive.

For example, libyang-Python's test environment selects its shared infrastructure
version once in `presubmit.json`:

```json
"consumer_deps": [
  {
    "name": "sonic-build-infra",
    "version": "0.0.6-553b2f70f9ba77b74befdf77674894166139ddcc",
    "repo_name": "sonic_build_infra"
  }
]
```

The runner generates both `bazel_dep` and a version-only `single_version_override`
from that entry. This prevents another dependency from silently selecting a
higher version, including a commit suffix that sorts higher despite belonging
to an older source revision. Arbitrary source, patch, and registry replacements
are not supported. The optional Rust preparation substitutes only a private copy
of the registry-fetched module, with generated dependency metadata. Its module
declaration must still exactly match the registry entry. Dependencies used by
the test environment must actually be fetched;
the runner fails if a declared dependency is missing or its fetched module name
or version differs. An empty `consumer_deps` list adds no pins.

Artifacts retain the generated `consumer.MODULE.bazel`, `MODULE.bazel.lock`,
each fetched dependency's `consumer-dep-<name>.MODULE.bazel`, and `consumer_deps` in
`validation.json`. These pins apply only to this CI test project. Downstream
repositories such as `sonic-swss-common` remain responsible for validating their
own dependency selection and integration builds.

Rust validation also retains the pinned helper, generated override, preparation
log and receipt, and the shared module's Cargo lock, generated Bazel metadata and
source-resolution record. The test consumer has no Cargo workspace of its own;
component-level Cargo compatibility remains covered by source CI.

### Prepare source-owned test runtimes

For a module whose source CI already prepares a locked test runtime, use:

```json
"test_runtime_preparation": {
  "script": "tools/bazel/runtime/prepare.py",
  "sha256": "<SHA256 of that file in the selected source archive>"
}
```

The runner verifies the fetched module and helper before executing it, after
building the selected outputs and before running **all** declared tests. It runs
the original helper from the independent consumer directory with `--lock` set to
that consumer's generated `MODULE.bazel.lock`, `--image-reference` set to the
job's pinned container image, and `--output` set to `test-runtime.json` in the
artifacts directory. The helper must support these arguments; the runner does
not invent package lists or use a lockfile shipped in the source archive.

The helper must use the lock's exact runtime package versions and checksums,
preserve existing container packages and keep project libraries under test out
of the system library directories. It must produce a JSON receipt containing
`architecture`, `image_reference`, `lock_sha256`, and `SONIC_TEST_RUNTIME_ID`,
alongside its selected packages and installed-library hashes. The identity is
the SHA256 of compact, key-sorted JSON for the receipt excluding
`SONIC_TEST_RUNTIME_ID`, `preserved_base_packages` and `lock_sha256`, matching
Common's existing preparation contract. The runner checks that identity and the
receipt's architecture, image and unchanged consumer lock. It passes the identity
as `--test_env=SONIC_TEST_RUNTIME_ID=...` so Bazel's test inputs include the
prepared runtime, without changing production build flags or dropping tests.

Runtime preparation requires root inside a disposable native Debian Trixie
container and an explicit `--test-container-image IMAGE@sha256:DIGEST` argument.
The workflow supplies its actual pinned image; local reproduction must start an
equivalent disposable container and pass that image reference. The runner refuses
host execution and missing container opt-in before starting a build. Merely
passing an image name does not start a container.

Artifacts retain `test-runtime-prepare.py`, `test-runtime.MODULE.bazel.lock`,
`test-runtime-preparation.log`, the helper's `test-runtime.json` receipt and any
adjacent logs, including on failure. `validation.json` records the opt-in and
test environment flag after every declared test passes.

## Maintain one MODULE declaration

For an entry whose source archive needs a MODULE overlay, opt in with
`"generated_module_overlay": true` in its `presubmit.json`. Maintain the complete
module declaration and dependencies in `modules/<name>/<version>/MODULE.bazel`.
Generate the source overlay and its checksum with:

```sh
python3 ci/registry_ci.py sync-module --module NAME --version VERSION
python3 ci/registry_ci.py sync-module --module NAME --version VERSION --check
```

The first command writes `overlay/MODULE.bazel` as a generated-file notice naming
`../MODULE.bazel` and the command, followed by the canonical bytes unchanged. It
also updates only that overlay's integrity field in `source.json`; the rest of
the source manifest remains maintained by hand. A missing overlay is created
after explicit opt-in. Do not edit the generated file or checksum separately.

`--check` writes nothing. Entry validation performs the same check before any
build, so a changed dependency or direct overlay edit fails even if someone
refreshes the overlay checksum manually. Repeated generation leaves matching
files untouched. Entries without this field keep their existing validation.

Bazel writes the canonical registry MODULE after applying source overlays and
patches. The fetched source MODULE must therefore match the canonical registry
MODULE exactly for every entry. The generated overlay is checked separately
before the build. `validation.json` records the canonical, fetched and optional
generated-overlay SHA256 hashes separately, plus `generated_module_overlay`.
`fetched_module_matches_registry` retains its literal byte-equality meaning.

## Native execution and source preservation

Every module uses the shared runner. Before building, it verifies the native
Linux CPU architecture and Debian userspace architecture. It records the exact
registry checkout commit and SHA256 hashes of the selected entry's source files
in `source-validation.json`. The entry must remain unchanged after validation,
including a failed build; mutation fails the job and is recorded in that receipt.
Work directories and artifacts stay outside the maintained entry.

Module-specific checks are ordinary Bazel tests selected in `presubmit.json`.
For example, Distroless's fixture-regeneration test runs its declared helper and
compares the output with the reviewed lock. It uses the same uncached execution
and test-result verification as the archive integration test, with no custom CI
driver or module/version branch in the workflow.

## Resolution and package evidence

The fresh consumer ignores `MODULE.bazel.lock` and uses `--lockfile_mode=update`.
The generated resolution state is copied to artifacts, including after a failed
build when the file exists; it is never committed to the registry. Successful
validation requires that Bazel generated this evidence.

Use explicit labels for required outputs and tests. Wildcard builds can silently
skip targets incompatible with the selected platform. Add tests to the module's
source, registry overlay, or a separate `integration_test_module`. Update the
corresponding overlay integrity hashes when changing overlay files. A successful library build alone does not establish
that downstream consumers can link it or that its runtime package works.

For example, the Distroless locked-import test has its own
`tests/integration/MODULE.bazel` declaring the APT extension, reviewed lock and
two imported package repositories. Its BUILD and Python test verify the archive
contents through that public interface. These are ordinary registry test files;
they need no test-only patch to the dependency's MODULE or source overlay. The
same CI invocation retains the dependency's existing external tests and runs
the root archive test on each configured native architecture.

Integration modules use the same registry, source checksum, fetched-module and
uncached-test checks as generated consumers. They cannot contain symlinks,
hidden configuration, cached lockfiles or Bazel output directories. CI copies
the files before execution, so generated lockfiles and test outputs stay outside
the maintained test directory. The chosen directory is recorded in
`validation.json`, and the staged MODULE and resolution lock remain artifacts.

For libyang, CI builds the runtime and detached-symbol packages, then runs
`libyang_test` and `libyang_package_test`. These cover a dynamic consumer, YANG and
JSON parsing, PCRE2 pattern validation, the SONiC validation flag, extracted
runtime execution, SONAME and symlinks, runtime dependencies, and matching debug
symbols with GDB source-line lookup. This is focused module validation; the
downstream `sonic-swss-common` pipeline remains responsible for its integration
tests.

## Download build outputs

Failed builds and tests retain local action stdout/stderr under
`failed-actions/`, including diagnostics larger than Bazel's console-output
limit. Each `index.json` records the action label, stream, retained path, byte
count and SHA256. Missing files, remote URIs and paths escaping the private work
directory are recorded as collection errors; they are never fetched or copied.
The original build or test failure remains the result.

Open **Actions → Registry CI → a successful run → Artifacts** and download
`registry-ci-<module>-<version>-<architecture>` (`amd64` or `arm64`). Each artifact
contains `registry-ci-evidence.tar`. Extract that first with
`tar -xpf registry-ci-evidence.tar` on a case-sensitive Linux filesystem.
It contains the complete job evidence: logs, manifests, failure diagnostics and
`outputs.json`, mapping required build targets to files under `outputs/` with
SHA256 hashes and sizes. There is no separate all-outputs `outputs.tar` format.

Generated file paths are preserved. Repository files reported without a Bazel
output prefix use their private workspace path under `outputs/source/`. For
example, `external/libc6/control.tar.xz` and `external/netbase/control.tar.xz`
remain separate even though both build-event records are named `control.tar.xz`.
Use the index instead of relying on a configuration
directory name. Directory outputs, such as prepared YANG models and execution
tool bundles, are retained as TARs under `outputs/trees/`. Their index records
have `type: "tree_archive"` and `root` naming the original output path inside the
TAR. Extract the TAR to preserve Unix modes, case-sensitive names, and relative
symlinks within the tree. GitHub's artifact ZIP format cannot faithfully retain
these properties and rejects some valid Linux filenames, including `:` in Perl
manual pages. Links to other outputs inside the build work directory are
materialized so each archive remains usable alone, as are relative links whose
meaning changes when copied into the archive. Links outside the build work
directory are rejected.
Archive ownership and timestamps are normalized; file modes are preserved.
The runner queries Bazel's declared directory outputs under the same build
configuration, since build events expand those directories into individual files.
The query selects `config(label, target)`: if the same target is also a build tool,
its execution configuration must not replace or duplicate the requested output.
Only files within those declared boundaries belong to a tree TAR; adjacent runtime
and debug TAR outputs retain their original bytes. The artifact includes
`declared-output-trees.jsonl` and the genuine build events for verification.

For native libraries, download the runtime and detached-debug packages from the
same module/version/architecture job. These packages come from the same build;
symbols from another run are not guaranteed to match. Extract package archives
to preserve their installed layout and modes. Standalone test launchers in the
artifact are build outputs, not portable installations with all runfiles.

The runner reads the successful build's default output groups, copies the
declared files, and fails if a required target or output is missing. It retains
outputs before running tests, so artifacts from failed jobs may contain packages
that have **not** passed validation. Check the job result and `validation.json`
before using them. Logs and other failure diagnostics remain available.

The two archive levels serve different consumers: `registry-ci-evidence.tar`
transports the complete job through GitHub unchanged, while each indexed directory
TAR is a reusable build output that can be downloaded and extracted separately.
Existing runtime/debug TAR files are not repackaged internally. For example,
`Text::CharWidth.3pm.gz`, `xt_CONNMARK.h`, and `xt_connmark.h` retain their names,
and a directory's executable files and portable relative links remain usable.


`test-results.json` indexes the `test.log` and `test.xml` files declared in each
Bazel test-result event, with its label, configuration, run, shard and attempt.
Files are retained under `test-results/` with SHA256 hashes and sizes. This also
captures tests in transitioned configurations, such as DASH API's Python test,
which are outside the default `bazel-testlogs` directory. The existing
`testlogs/` snapshot remains available for compatibility. A collection error
fails otherwise successful validation; after a build or test failure it is
recorded in `test-results-error.json` without replacing the original failure.
If that receipt cannot be written, the error is printed to stderr and the
original validation failure is still preserved.

## Environment and coverage

The build matrix uses native GitHub-hosted `ubuntu-24.04` and `ubuntu-24.04-arm`
servers with a `debian:trixie-20260918` container pinned to its multiarch image
digest. It installs the compiler and
package-test tools in the container and downloads Bazel 8.5.1 with a pinned SHA256
for the native CPU. GitHub actions are pinned to commit SHAs, checkout does not
persist credentials, and the workflow uses read-only repository permissions.

Runner tests execute on native AMD64 and ARM64 hosts with pinned Bazel 8.5.1.
They build an actual directory-producing target and its public alias, including
both target and execution configurations, then check collection and extraction.
Transport and failure-log tests also cover rejected paths, partial archives,
case-sensitive filenames, Unix modes, empty directories and symlink relocation.

Each job uses a fresh consumer and Bazel output directory. There is no saved Bazel
cache in this initial workflow. Logs, Bazel build-event files, available test
logs, and validation metadata are retained as workflow artifacts for 14 days,
including when module validation fails. Setup failures can occur before these
files exist and remain visible in the Actions job log.

ARMHF, cross execution, other operating systems, all historical registry entries,
and the complete SONiC image are outside this matrix. Declaring an ARMHF layout
in a module does not establish ARMHF build or execution coverage.

## Local reproduction

Use a native AMD64 or ARM64 Debian trixie environment with Bazel 8.5.1 and
`binutils`, `build-essential`, `ca-certificates`, `gdb`, `git`, `python3`, `tar`,
`curl`, and `xz-utils`. From the registry checkout, inspect the plan and run the
selected module:

```sh
git fetch origin main
python3 ci/registry_ci.py plan --latest \
  --published "$(git rev-parse origin/main)" --head "$(git rev-parse HEAD)" \
  --output /tmp/registry-ci-plan.json
python3 -m unittest discover -s ci/tests -v
python3 ci/registry_ci.py run \
  --module libyang \
  --version 3.12.2.sonic.1 \
  --architecture amd64 \
  --work-dir /tmp/registry-ci-libyang-amd64 \
  --artifacts /tmp/registry-ci-libyang-amd64-artifacts
```

Use `--architecture arm64` on a native ARM64 server. `--bazel /path/to/bazel`
selects a specific Bazel executable. To inspect a PR's selection, replace
`--latest` with `--base <actual-PR-base-commit>` and check out the desired head first.
Use `--all` to include every configured historical version. Keep `--published`
set to the freshly fetched maintained `main` SHA, even for a stacked PR. Keep
the work and artifact directories outside the registry checkout and use a fresh work directory for a
clean reproduction.

See the [Bazel registry format](https://bazel.build/external/registry) for module
source, patch, and overlay metadata.
