# Registry CI

Registry CI validates a module as a dependency in a fresh Bazel consumer. It
resolves the module from the proposed registry checkout, then builds the declared
outputs and runs explicit consumer and package tests. This exercises registry
resolution, archive integrity, patch and overlay application, compilation, and
the behavior covered by each module's tests.

The workflow runs on every pull request, pushes to `main`, and manual dispatches.
Each push to `main` and each manual dispatch gets its own run. A new PR revision
cancels the previous automatic run for that PR. Retrying a job on an older
revision leaves other runs in progress.

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
passes only when planning, both native unit jobs, the explicit cross fixture,
and every selected module job pass. A skipped module matrix is accepted only
after successful planning explicitly selected no jobs. Adding the workflow does not itself change
repository branch-protection settings.

## Verified source mirrors

For new GitHub-backed input sets, use the [shared manifest reader](github_sources/README.md)
rather than adding a package-specific downloader. It retains the approved private
Debian mirror path, checks GitHub redirects and verifies the selected bytes before
starting Bazel. Its first data manifest generalizes registry #238's three Cosmos
inputs without changing their versions or checksums. Other new download locations
require explicit user approval; the existing transports below are not broadened
or rewritten by this reader.

The runner passes Bazel's standard `--experimental_downloader_config` with
[`source_mirrors.cfg`](source_mirrors.cfg) to dependency preparation, builds,
tests and output queries. Rewrites match only the archive and binary-package
URLs described below; registry order, module versions, source recipes and
integrity values stay unchanged.

BCR `pigz@2.8.bcr.2` requests `https://zlib.net/pigz/pigz-2.8.tar.gz`.
That exact URL now tries the verified
[`pigz-2.8.tar.gz` release asset](https://github.com/securely1g/sonic-bazel-registry/releases/download/ci-source-mirrors-20261104/pigz-2.8.tar.gz)
first, followed by the existing MacPorts mirror. Both must match BCR's unchanged
SHA256 `eb872b4f0e1f0ebe59c9f7bd8c506c4204893ba6a8492de31df416f0d5170fd0`;
BCR still applies its original source patches. For example,
[buildimage #133](https://github.com/securely1g/sonic-buildimage/pull/133)
can pass this shared downloader configuration for its source-base and OCI builds instead
of downloading pigz with a separate `prepare_pigz.py` helper. An unavailable or
corrupt release asset falls back to MacPorts; corrupt bytes from both candidates
fail the fetch and cannot enter Bazel's verified repository cache.

The five ARM-hosted BCR archives use verified copies in this repository's
[source-mirror release](https://github.com/securely1g/sonic-bazel-registry/releases/tag/ci-source-mirrors-20261104)
first, with each original GitLab release URL retained as the next candidate:

| BCR module | Release asset |
| --- | --- |
| `ape@1.0.1` | `ape-v1.0.1.tar.gz` |
| `download_utils@1.0.1` | `download_utils-v1.0.1.tar.gz` |
| `rules_coreutils@1.0.1` | `rules_coreutils-v1.0.1.tar.gz` |
| `rules_gzip@1.0.0` | `rules_gzip-v1.0.0.tar.gz` |
| `toolchain_utils@1.0.2` | `toolchain_utils-v1.0.2.tar.gz` |

Each copy must satisfy the original BCR SHA512 integrity. This avoids the
[ARM GitLab release endpoint failures](https://github.com/bazelbuild/bazel-central-registry/issues/9973)
without discarding the upstream source. Bazel 8.5.1's
[URL rewriter](https://github.com/bazelbuild/bazel/blob/8.5.1/src/main/java/com/google/devtools/build/lib/bazel/repository/downloader/UrlRewriter.java)
collects matching replacements in configuration order; its
[downloader](https://github.com/bazelbuild/bazel/blob/8.5.1/src/main/java/com/google/devtools/build/lib/bazel/repository/downloader/HttpDownloader.java)
tries the next candidate after a failed download or checksum mismatch. Other
versions and URLs are unaffected; no global module mirror is enabled.

Historical Common builds use GNU Bison 3.3.2 and GNU M4 1.4.18 through
libnl3. Registry CI tries the MacPorts copy of Bison and Debian's byte-identical
upstream M4 TAR, then the declared GNU locations. Trusted Trixie jobs take the
M4 TAR from the private Debian source pool first. Both archives must match the
original rule's SHA256. [Bison release pin](https://github.com/jmillikin/rules_bison/blob/v0.4/bison/internal/versions.bzl#L17-L30) · [M4 release pin](https://github.com/jmillikin/rules_m4/blob/v0.3.1/m4/internal/versions.bzl)

The exact `gawk-5.3.2.tar.xz` URLs at `mirrors.kernel.org`, `ftp.gnu.org`, and
`ftpmirror.gnu.org` likewise try MacPorts first and retain each original URL as
a fallback. The published source recipe and SHA256
`f8c3486509de705192138b00ef2c00bbbdd0e84c30d5c07d23fc73a9dc4cc9cc` remain unchanged.

Some packages have additional exact-URL candidates before their timestamped
snapshot fallbacks:

| Locked package | Additional candidate |
| --- | --- |
| `libcap-dev_2.75-10+deb13u1+b1_amd64.deb` | Debian content-addressed file |
| `libaudit-dev_4.0.2-2+b2_amd64.deb` | Debian content-addressed file |
| `libcap2_2.75-10+deb13u1+b1_arm64.deb` | Verified GitHub release copy |
| `bash_5.2.37-2+b9_arm64.deb` | Verified GitHub release copy |
| `libc-bin_2.41-12+deb13u3_arm64.deb` | Debian content-addressed file, then existing CDN fallback |
| `uuid-dev_2.41-5_amd64.deb` | Debian content-addressed file, then existing CDN fallback |
| `libc-ares-dev_1.34.5-1+deb13u1_arm64.deb` | Debian content-addressed file, then the official security CDN |
| `openssl-provider-legacy_3.5.6-1~deb13u2_arm64.deb` | Debian content-addressed file |
| `openssl_3.5.6-1~deb13u2_arm64.deb` | Debian content-addressed file |

These candidates preserve each original APT-lock SHA256. The SHA1 in Debian's
content-addressed URL is only a locator; Bazel still checks the stronger locked
SHA256. The GitHub copies have a [checksum and origin manifest](https://github.com/securely1g/sonic-bazel-registry/releases/download/ci-source-mirrors-20261104/debian-package-mirrors-20261105.json).
Their rewrites match the exact timestamp, version, and architecture. Local HTTP
fixtures exercise the added candidates, fallback to the original paths, and
rejection of corrupt mirror bytes. Cold Bazel fetches verify the five packages
selected by the hosted ARM jobs against their original locked hashes and sizes;
neither architecture's package binaries are executed by these fetch tests.

Other timestamped `snapshot.debian.org/archive/debian/.../pool/*.deb` downloads
try the identical pool path on Debian's official `deb.debian.org/debian/` CDN
first, then retain the exact timestamped snapshot URL as fallback. This avoids
transient snapshot HTTP 503 failures for package versions still present in the
current pool; older packages absent from the CDN continue through the snapshot.
Binary-package inputs on `snapshot-cloudflare.debian.org` try the identical CDN
pool path, then the identical timestamp/path on `snapshot.debian.org`, then the
original Cloudflare snapshot URL. The native AMD64 and ARM64 BusyBox 1.36.1-6
packages declared by `rules_coreutils@1.0.1` retain all three candidates, with
cold-fetch regressions checking both original SHA256 hashes without executing
either package.
The locked filename, version and SHA256 remain unchanged. The generic rules do
not rewrite indexes, metadata, source archives, or `debian-security`; only the
three exact security-package exceptions listed above are added. The cold-fetch
regression checks `libsframe1_2.44-3_amd64.deb` against
its generated APT lock's SHA256
`38f625dfdc582717029ac3a3e97c51d994ec2e7a0e9b230c6b44e40d1276311f`.

Repository downloads allow 12 HTTP connection attempts with a nominal 10-second
retry-delay cap and at most four parallel downloads per Bazel process. These flags
apply to both architectures, repository-dependent commands and Rust preparation;
the cold-fetch regressions use the same policy. This allows transient HTTP
503/504 responses to recover without changing package inputs or retrying tests.

BCR `pigz@2.8.bcr.2` is used by build-infra's reproducible gzip tool when packaging
WPA's debug TAR. Its original URL now serves different bytes; a clean
[WPA registry build](https://github.com/securely1g/sonic-bazel-registry/actions/runs/41587703074/job/125760920377)
fails its BCR checksum before compiling any source.

The MacPorts mirror retains the original archive with SHA256
`eb872b4f0e1f0ebe59c9f7bd8c506c4204893ba6a8492de31df416f0d5170fd0`.
Bazel still verifies BCR's unchanged integrity and applies its unchanged patches.
No source/version override, custom module, or disabled integrity check is involved.

This config applies automatically in this registry's validation runner. It does
not change how standalone consumers download dependencies. Until BCR's upstream
source location is repaired, standalone callers can opt in using an absolute
path to a checkout of this config:

```sh
bazel build --experimental_downloader_config=/path/to/sonic-bazel-registry/ci/source_mirrors.cfg //your:target
```

The real Bazel runner tests fetch the five ARM archives, gawk, BCR's pigz and the
locked Debian package into new, empty repository caches without a distdir,
checking original archive hashes and
fetched MODULE files. Local HTTP fixtures verify candidate order, fallback after
HTTP errors and checksum mismatches, and rejection when every candidate has the
wrong bytes. These are repository fetches; they execute no compilation or package
actions.

## Private Debian snapshot mirrors

Trusted jobs on the self-hosted `debian-trixie-container` and
`debian-trixie-container-large` runners can prefer
private Debian mirrors while keeping the published package URLs and checksums.
Configure these optional **Actions repository secrets** under **Settings →
Secrets and variables → Actions**:

| Secret | Stable HTTPS archive root |
| --- | --- |
| `DEBIAN_MIRROR_ROOT` | Private URL ending in `/archive/debian/` |
| `DEBIAN_SECURITY_MIRROR_ROOT` | Private URL ending in `/archive/debian-security/` |

CI appends the snapshot timestamp from [debian_snapshots.json](debian_snapshots.json).
Set these two secrets once. Trusted jobs select the secret pair after checkout.
A pre-manifest helper uses the existing dated secrets, including when it runs
under a newer workflow.
Do not put the values in registry files, workflow variables, container images,
PR descriptions, or reproduction commands. The public workflow refers only to
the secret names. It passes them explicitly to the reusable module workflow
for same-repository pull requests, maintained-branch pushes, and manual runs,
excluding Dependabot. The receiving workflow also checks its runner and event before forwarding secrets.
Trusted AMD64 module builds, ARM64 cross builds, native runner tests and the
cross-compiler fixture share the same routing. Hosted ARM64 and fork runs use
the public configuration.

The downloader maps each Debian input according to its published identity:

| Input | First private candidate |
| --- | --- |
| Dated Debian or security snapshot | The same archive, original timestamp and path. This includes the December 2024 Socat sources and February 2024 BusyBox packages. |
| Official CDN binary pool URL | The archive's current snapshot from the manifest and the original pool path. |
| Official CDN source archive or source descriptor | The matching undated CDN pool path, such as `/debian/pool/...`. |
| Snapshot content address | The same `/file/<SHA1>` object, verified against the caller's independent integrity pin. |

For example, the Trixie APT resolver starts several compressed versions of
`Packages` and `Contents` in parallel. A private `Packages.xz` success does
not cancel an already running `Packages.gz` request. Mirror the formats listed
in the signed Debian Release files, including `Contents.gz` for each target
architecture. Public fallback remains available for every published format.
For each retained timestamp, the manifest records the signed formats for
`Packages` and `Contents` by suite. Probes for unpublished encodings stay
on the private endpoint. This covers the `main` indexes for AMD64, ARM64 and
ARMHF. A Trixie build can evaluate a component's Bookworm extension while
resolving its module graph.

### Roll the CI mirror to a new snapshot

1. Stage the new dated directory on the private mirror. Verify the signed
   Release metadata and the index and package files that consumers use.
2. Edit **only [debian_snapshots.json](debian_snapshots.json)**. For each archive
   being rolled, add its timestamp under `snapshots`, record the signed
   `Packages` and `Contents` suffixes for each supported suite, and set
   `current` to that timestamp. An empty suffix represents the raw index.
   Verify the archive's `probe` package path and SHA256 against the new
   snapshot. Update them if its package changed.
3. Keep previous entries and their mirrored files while consumers still pin
   those releases. Bazel preserves timestamps on dated URLs. Direct APT
   preparation uses the per-date mapping for every retained entry.
4. Run `python3 -m unittest discover -s ci/tests -p test_debian_snapshot_rollover.py`
   to exercise old and new routing with the same roots. Run **Registry CI**
   with **private_mirror_probe** and check the evidence for
   both archives. The probes fetch from the current dates with a fresh cache
   and public fallback disabled.

This procedure changes CI mirror routing. To upgrade the Debian packages a
component selects, publish the corresponding dependency pins in the owning
module and update its consumers separately.

Temporary configuration lives outside the artifact directory. The wrapper
removes mirror values from the child process environment and registers them
for GitHub masking. Module validation supplies an ephemeral APT mirror map
to runtime preparation because direct APT calls use a separate transport.
The checked preparer and package locks still verify the selected runtime.

Bazel preparation commands such as the ARM toolchain provider's `fetch` retain
redacted fetch events alongside the usual build/test event streams. Before
upload, CI scans diagnostics and nested artifacts for private locations. On a
trusted job, `debian-downloads.json` identifies the evidence files, successful
and failed candidates, APT Get activity, and any public or unattributed transfers.
A warning points to this report if there are exceptions. A Bazel fetch event identifies the selected candidate.
Bazel 8.5.1 omits the entire build event stream for `mod` and `info`;
`mod graph` can still download packages while evaluating module extensions.

The Trixie planning job compiles the checked-in observer with its existing Java compiler.
Validation jobs download the JAR by its artifact ID from the same workflow run
and compare its embedded source SHA256 with their checkout before loading it.
For trusted runs, this observer delegates to the JVM's existing HTTP
cookie handler and records the actual Debian request and response origins.
It captures fast requests, public fallback and redirects in those commands.
The observer records the origin class, safe object path and HTTP status. It
omits private hosts, queries, user information, cookies and authentication
headers. A missing or unhealthy JVM receipt is flagged as incomplete. Retained
event files are under `download-traces/http/`.

Read the evidence by type. An HTTP 200 means a server responded; the returned
bytes can still fail integrity verification. Bazel's successful fetch events,
the checked package digests, and APT's verified installation receipts provide
separate evidence. A repository cache hit can complete without an HTTP request.


To prove private mirror availability, manually run **Registry CI** with
**private_mirror_probe** selected. This optional check runs only on the trusted
self-hosted Trixie runner and requires both mirror secrets to be configured.
It uses the same `sudo` environment as local module validation, so it cannot
depend on proxy settings available only to the runner user. It performs
fresh-cache Bazel downloads of each archive's manifest-selected probe package,
checks its SHA256 and retains a sanitized receipt.
Ordinary pull-request and push CI use public fallback and do not require the
private mirrors to be available. The manual probe defaults to off and does not
change the module validation matrix. Local regression tests cover mirror
preference, public fallback, checksum rejection, and console/artifact redaction.
The explicit probe fails when either secret is missing; ordinary builds still
use public sources.

This protects the URLs from public source and normal published evidence. Code
executing in a job that receives the secrets can read them; the profile is for
trusted code, not an isolation boundary against a malicious workflow or build.

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

For source versions with the same numeric release, the last registration in
`metadata.json` wins. Git hashes do not indicate which commit is newer. Append
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

- `architectures`: target architectures to validate, currently `amd64` and/or
  `arm64`. Execution remains native unless an exact ARM version is selected for
  staged cross validation.
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
- `additional_targets` (optional): append build or test labels for a declared
  target architecture. The nonempty top-level lists run on every architecture.
  For example, the DocBook runtime and its test require AMD64 execution tools.
  A native AMD64 registration can add those labels under `amd64` while ARM64
  runs the common targets. Cross jobs select by target architecture. Commands,
  required output artifacts, verified tests and the receipt use that same list.

  ```json
  "additional_targets": {
    "amd64": {
      "build_targets": ["@sonic-build-infra//tools/build_tools:docbook_runtime"],
      "test_targets": ["@sonic-build-infra//tools/build_tools:docbook_runtime_test"]
    }
  }
  ```

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

### Route source-owned runtime preparation through private APT mirrors

Compatible preparers can opt into this CI-only presubmit field:

```json
"test_runtime_preparation": {
  "script": "tools/bazel/runtime/prepare.py",
  "sha256": "<unchanged source helper SHA256>",
  "apt_mirror_protocol": "locked-runtime-v1"
}
```

The protocol requires the verified helper's existing `select_runtime(lock,
architecture)`, `snapshot_sources(selected, architecture)`, `inventory()`,
`missing_packages(selected, before)`, and `verify_inventory(selected, before,
after)` functions. All five current Common entries use the same compatible
helper. Other helpers retain their normal execution path; a mirror secret alone
does not opt them into this protocol.

For trusted Trixie jobs the mirror wrapper supplies `SONIC_APT_MIRROR_CONFIG`,
the path to a temporary mode-0600 JSON file outside artifacts. Its schema is
`{"schema_version": 1, "mirrors": {"<canonical HTTPS snapshot base>":
"<preferred HTTPS mirror base>"}}`; canonical keys have no trailing slash.
The CI adapter first uses the owner's exact resolved package selection and
provenance check. Standard APT then uses local `mirror+file` lists with the private
endpoint at priority 1 and the canonical public endpoint at priority 2. APT
handles fallback for each file. The lists are mode 0400 and owned by `_apt`,
so its normal sandbox can read them without making private endpoints readable
by other unprivileged container users. No system APT configuration is changed.

Signature checks, simulated dependency planning, refusal to change prepared-base
packages, selected version/architecture/SHA256 checks, and installation without
further downloads remain enforced. The original source helper then executes
unchanged and performs its normal runtime validation and receipt generation.
The additional step runs in the same target environment, including the ARM
executor when selected. Without a private map, normal public preparation remains
available.

`test-runtime-mirrors.json` records selected and verified packages, the before/after
inventory, and configured snapshot mappings without private endpoints. The
configured mappings alone do not establish where bytes came from: the adjacent
`test-runtime-mirrors.apt.log` contains actual APT acquisition evidence. Ignore
local `file:... Mirrorlist` reads when counting network transfers. The existing
mirror wrapper scrubs and scans these files before upload. Common's normal
`test-runtime.apt.log` is empty after successful pre-provisioning because the
unchanged helper finds no missing packages and makes no second APT download.

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

Bazel 8.5.1 can report a Unicode tree member using UTF-8 bytes interpreted as
Latin-1, together with a damaged file URI. For example, registry CI's real
artifact fixture reported `Főtanúsítvány.crt` as `FÅ\x91tanÃºsÃ\xadtvÃ¡ny.crt`
on its AMD64 worker. When that literal basename is absent, the runner tries
one strict Latin-1-to-UTF-8 conversion of the basename. The result must be a
regular file inside the declared tree, with the build event's exact SHA256 and
size; URI-parent, ASCII-name and path-safety checks still apply. Existing
literal names are never reinterpreted, and recovery through a symlink is
rejected. The TAR retains the actual filesystem name and bytes. This does not
change Bazel's locale or repair arbitrary paths. The failed worker's effective
JVM locale was not retained.

The real Bazel collector fixture creates its certificate filename with ASCII
shell octal escapes and checks its exact UTF-8 bytes before collection. Its two
producer actions (target and execution configurations) use
`execution_requirements = {"no-remote-cache": "1"}`. This prevents those actions
from reading or uploading remote cache results while retaining sandboxing,
reuse of existing local action outputs, analysis reuse and caching for the separate tool action and all
module builds. The observed runner command configures a remote cache, not a
remote executor; this action requirement does not disable remote execution.

This isolates collector validation from an unresolved Bazel 8.5.1 remote tree
transport defect. A retained AMD64 run materialized a double-encoded Unicode
filename from cached output and failed the strict filesystem assertion before
the collector ran. The earlier passing run also reported a Unicode runtime
backport, so it is not a controlled cache-only comparison. The fixture keeps
all filesystem, BEP, target-versus-execution configuration and final TAR checks.
Passing it does not establish that production remote tree transport is fixed;
this change neither modifies the Bazel runtime nor changes production caches.

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

Planning, the aggregate check, AMD64 runner tests, and ordinary local module
validation use `self-hosted`, `Linux`, `X64`, and `debian-trixie-container`.
P4C (`p4c`), BMv2 (`p4lang-bmv2`), and DASH (`sonic-dash`) use
`debian-trixie-container-large` as their fourth label whenever their execution
architecture is AMD64. This includes qualified ARM64 cross jobs and the P4C host
tool built inside DASH. An ARM64 version that requires native execution still
uses its usual GitHub-hosted ARM runner. Both Trixie pools use the same source
mirrors, private-mirror trust checks, HTTP audit, and package tools.

The large pool on `lgh108` provides four concurrent jobs, each limited to 8
CPUs and 16 GiB. These limits may be overcommitted on the node. The ordinary
pool retains its existing 16-slot, 6 GiB-per-slot configuration. Register both
pools as ephemeral so each runner
accepts only one job; `sonic-slave-wrk-mgr` must remove the finished container
and replace it with a fresh registered runner after success, failure, or
cancellation. Keep registration credentials in the manager, outside job
containers, and retain runner diagnostics before removing a container.

This staged migration sets `ARM_CROSS_ALL = False`. Only the exact module
versions in `ARM_CROSS_VERSIONS` use native AMD64 cross-compilers and the ARM
runtime executor inside the Trixie runner. Every other ARM version retains its
native GitHub-hosted ARM route, including newer versions of a migrated module.
All original build labels, test labels, sources and dependency pins remain
unchanged. The separate all-ARM survey supplies the acceptance evidence below;
failed or incomplete contracts remain on native ARM while fixes are validated.

Module steps execute directly inside the disposable runner, built from the
pinned Trixie base with compiler and package-test tools preinstalled.
Before Bazel runs, module validation and native/cross runner tests invoke
[`prepare_repository_tools.sh`](prepare_repository_tools.sh). APT repository
evaluation needs the host's `file` command and magic database to distinguish
GNU linker scripts from ELF libraries. For example, ncurses' `libncursesw.so`
contains `INPUT(libncursesw.so.6 -ltinfo)`; it must be classified as text rather
than passed to `readelf` as an ELF file. The helper installs Debian package
`file` when the command is missing, using sudo only for a non-root runner, and
always checks this MIME classification. Failed package installation or an
unusable magic database fails the job before repository evaluation. Hosted
ARM module jobs also include `file` in their normal build-tool package list.
The helper works with existing ephemeral images; preinstalling the package
in the registry runner image avoids the bootstrap download.

AMD64 does not start a second container or require a Docker daemon. Actions run
as UID 1000; module validation and runtime package preparation use passwordless
`sudo` inside the disposable container. Evidence is archived as root, then only
the resulting TAR is given to the action user, preserving the archived modes.

The manager supplies `SONIC_RUNNER_IMAGE_REFERENCE=sonic-slave-runner@sha256:...`
from the actual derived image's inspected Docker image ID. This is a local
content identity, not a registry pull reference or the upstream base digest.
`validation.json` records the actual local runner identity for native AMD64 and
cross ARM jobs, or the pinned job image for hosted native ARM. Missing local
runner identity fails validation. Runtime preparation receipts
also record the prepared package inventory and library hashes.

The AMD64 image contains the checksum-verified Bazel 8.5.1 binary at
`/usr/local/lib/bazel-8.5.1`. Its `/usr/local/bin/bazel` wrapper explicitly passes
the image's Java CA trust store as a startup argument, including when CI ignores
all bazelrc files. The workflow verifies the binary's checksum again. ARM cross jobs use that same native AMD64 Bazel binary. GitHub
actions are pinned to commit SHAs, checkout does not
persist credentials, and the workflow uses read-only repository permissions.

Local native AMD64 and cross ARM module jobs pass
`--bazel-startup-arg=--host_jvm_args=-Xmx2g` to bound
Bazel's Java heap within the worker's memory limit. The runner accepts
repeated startup arguments, forwards them to build, test, cquery, info and Rust
preparation, and records them in `validation.json`. Hosted native ARM keeps its
default heap.
Repeated `--bazel-build-arg` options reach build, test and output queries.
Local module jobs use `--jobs=1` and `--discard_analysis_cache` to reduce
concurrent compiler memory. Rust preparation receives those settings too.
On a large runner, the P4 recipes can use their own `make -j4` within one
Bazel action. The job verifies an effective 8-CPU cgroup quota, at least 8 CPUs
in its affinity, and a 16 GiB memory limit before starting validation. Its
`p4-runner-resources.json` artifact records these limits, the command exit code,
and the job cgroup's available memory peak and OOM counters before and after
Bazel. For locally executed CMake and Make actions, it also reads Bazel's
existing build and test event files. For each reported action mnemonic, it
divides the accumulated user and system CPU seconds by the wall time between
its first start and last finish. With multiple actions this gives average cores
over the group's span, including gaps. Bazel's action count can include cache
hits, which add no local CPU time. Missing CPU metrics and phases with remote
execution are reported without a cores estimate. This measurement records CPU
consumption of the whole recipe, including its child processes.
[Bazel build metrics](https://github.com/bazelbuild/bazel/blob/8.5.1/src/main/java/com/google/devtools/build/lib/buildeventstream/proto/build_event_stream.proto#L847-L873).

The default repository Actions variable setting is
`REGISTRY_P4_RUNNER_PROFILE=large` (also selected when the variable is unset).
GitHub waits for an available runner matching the plan's exact labels. If
large workers are offline, set the variable to `standard` and **start a new
run that executes planning**. The resulting jobs use the ordinary pool and
append `--eval=.NOTPARALLEL:` to target and execution-platform `GNUMAKEFLAGS`
to fit 6 GiB. Retrying only an already-planned job retains its previous label.
Restore the variable to `large` or remove it to resume the large route. Check
the P4 jobs' resource artifacts after enabling a new pool.

These three local jobs have a six-hour deadline. A single
local module matrix combines native AMD64 and staged cross ARM jobs, with at most ten running
per workflow run. Hosted native ARM has its own matrix. This is a module limit
per run, not a host-wide limit across runs; planning, native unit tests, the cross
fixture and the aggregate also use workers. Both module groups and both test
suites are required by the aggregate `Registry CI` check. Empty module groups are
accepted only when planning explicitly reports them empty.

Tests receive an explicitly exported empty `HOME`, which Bazel's test setup
replaces with that test's writable `TEST_TMPDIR`. This lets Python and other
subprocesses create user configuration inside the test sandbox; an absent
`HOME` would otherwise fall back to the account's home directory.

`TestRunner` actions prefer `processwrapper-sandbox`. This lets tests hard-link
their declared runfiles into writable temporary directories and set executable
permissions on those private copies. Build actions keep their existing sandbox
strategy. Local or exclusive tests retain the `local` fallback, and real Bazel
regressions cover both paths without changing published tests.

The native helper suite runs on both AMD64 Trixie and GitHub-hosted native ARM64
with the matching checksum-pinned Bazel 8.5.1 binary. Native ARM helper coverage
remains required while any modules retain that route. The separate required
cross fixture tests native execution tools, ARM compilation and ARM runtime
behavior; it does not replace or claim native ARM Bazel execution coverage.
`run_runner_tests.py --suite native` discovers every test file except the ARM
cross-runtime fixture. A separate local job runs `--suite cross` with a 60-minute
bound, both executable prerequisites explicitly set and checked, and failure on
any skipped cross test. A regression verifies that these suites partition full
discovery without overlap or omissions. The native tests build an actual
directory-producing target and its public alias, including both target and execution configurations, then check collection and extraction.
Transport and failure-log tests also cover rejected paths, partial archives,
case-sensitive filenames, Unix modes, empty directories and symlink relocation.

Each job uses a fresh consumer and Bazel output directory. Logs, Bazel build-event files, available test
logs, and validation metadata are retained as workflow artifacts for 14 days,
including when module validation fails. Setup failures can occur before these
files exist and remain visible in the Actions job log.

ARMHF, other operating systems and the complete SONiC image are outside this
matrix. Pull requests validate latest configured versions; the explicit
`all_versions` dispatch also surveys configured historical versions.
Declaring an ARMHF layout in a module does not establish ARMHF build or execution coverage.

## Staged ARM64 cross validation

The shared helper has an explicit cross mode. Each planned row records target
`architecture`, native `execution_architecture`, and a boolean `cross_compile`.
Native callers retain their defaults; cross execution requires both
`--cross-compile` and an absolute executable `--test-executor`, an AMD64 host,
an ARM64 target, and an explicit disposable Debian Trixie container identity.
The reusable workflow selects native Bazel, image, sudo and artifact handling by
execution mode while preserving the target architecture and all original labels.

The `ARM_CROSS_VERSIONS` map selects exact module versions for the Trixie
cross-build pool. The initial 15 versions were validated in the [all-ARM
survey](https://github.com/securely1g/sonic-bazel-registry/actions/runs/42013547416).
Job artifacts record the selected dependency versions, native execution and ARM
target platforms, output identities, and results of the original uncached tests.
Historical versions outside the map use hosted ARM64.

| Module | Exact version | Build / test labels | ARM64 validation |
| --- | --- | --- | --- |
| `gawk` | `5.3.2.sonic.1` | 3 / 1 | [Passed](https://github.com/securely1g/sonic-bazel-registry/actions/runs/42013547416/job/127198380280) |
| `gazelle` | `0.54.0.sonic.1` | 1 / 3 | [Passed](https://github.com/securely1g/sonic-bazel-registry/actions/runs/42013547416/job/127198380420) |
| `libnl3` | `3.7.0.sonic.7` | 5 / 4 | [Passed](https://github.com/securely1g/sonic-bazel-registry/actions/runs/42013547416/job/127198380378) |
| `libyang-python` | `3.1.0.sonic.6` | 4 / 3 | [Passed](https://github.com/securely1g/sonic-bazel-registry/actions/runs/42013547416/job/127205852291) |
| `protobuf-legacy` | `3.21.12.sonic.2` | 8 / 4 | [Passed](https://github.com/securely1g/sonic-bazel-registry/actions/runs/42013547416/job/127218315473) |
| `rules_foreign_cc` | `0.16.0.sonic.1` | 2 / 1 | [Passed](https://github.com/securely1g/sonic-bazel-registry/actions/runs/42013547416/job/127221268640) |
| `rules_python` | `1.9.0.sonic.1` | 3 / 1 | [Passed](https://github.com/securely1g/sonic-bazel-registry/actions/runs/42013547416/job/127230792181) |
| `sai` | `1.18.0-sonic.1` | 2 / 3 | [Passed](https://github.com/securely1g/sonic-bazel-registry/actions/runs/42013547416/job/127259342573) |
| `socat` | `1.8.0.2.sonic.5` | 4 / 1 | [Passed](https://github.com/securely1g/sonic-bazel-registry/actions/runs/42013547416/job/127316394685) |
| `sonic-dash-api` | `0.0.5-9b2893e890734a2db0c53a5e5c64b031ec0dcfbd` | 8 / 5 | [Passed](https://github.com/securely1g/sonic-bazel-registry/actions/runs/42013547416/job/127363604452) |
| `sonic-linux-kernel` | `0.0.2-34a53faaecd325509e9d8f1016ed0108ab558a23` | 5 / 5 | [Passed](https://github.com/securely1g/sonic-bazel-registry/actions/runs/42013547416/job/127391886151) |
| `sonic-rust-deps` | `0.0.4-6d9c70f708d7420e9e2b2cdc906b80cee6b140f1` | 6 / 4 | [Passed](https://github.com/securely1g/sonic-bazel-registry/actions/runs/42013547416/job/127417149111) |
| `sonic-sairedis` | `0.0.5-33443ea1666a23812365d03fb959066ee84c9aa0` | 19 / 7 | Pending current registration validation; [historical generator run](https://github.com/securely1g/sonic-bazel-registry/actions/runs/42237091438) |
| `sonic-swss` | `0.0.3-9c3797990d4b5a79100a40fe7689927c18212361` | 7 / 3 | Pending current registration validation; [historical generator run](https://github.com/securely1g/sonic-bazel-registry/actions/runs/42238852494/job/127963546293) |
| `sonic-yang-mgmt` | `1.0.0-9ab452d22773c41783092ae3bd6c206d6c257c8d` | 2 / 1 | [Passed](https://github.com/securely1g/sonic-bazel-registry/actions/runs/42013547416/job/127454762848) |
| `sonic-yang-models` | `1.0.1-b0a9362a7a1b4b5e1b7188c019d256f7c8aaff9f` | 3 / 1 | [Passed](https://github.com/securely1g/sonic-bazel-registry/actions/runs/42013547416/job/127456801062) |
| `tar.bzl` | `0.10.5.sonic.2` | 8 / 7 | [Passed](https://github.com/securely1g/sonic-bazel-registry/actions/runs/42013547416/job/127457427548) |

The `linux-kernel` contract validates its declared helpers; it does not build or
boot a kernel image. Passing tests only establish each module's existing
presubmit contract, not broader undeclared functionality. Yang-model package outputs and TAR
regression archives are architecture-neutral; their original target-side runtime
tests remain required, and native execution tools retain their configurations.

The initial survey also found that QEMU user-mode returns `ENOSYS` to Linux
AIO in `rules_distroless@0.9.4.sonic.17`. Its ARM job runs the original
`linux_headers_test` executable under a Debian ARM64 kernel using QEMU system
emulation. The other 35 tests use the image's standard executor. The guest
includes the runner's ARM loader and libc. Its console reports the test exit
status to Bazel. [Full ARM validation](https://github.com/securely1g/sonic-bazel-registry/actions/runs/42089131813/job/127462206254)

The `rules_go` `0.65.0.sonic.1` follow-up moves both original test targets to
the cross runners. Their ARM test processes invoke the native Bazel launcher
inside fresh workspaces. Nested builds use the same cross compiler and sysroot
as the outer build and check the architecture of each produced executable.
All four original Go cases passed, including Cgo header propagation and build ID
changes. [Full ARM64 validation](https://github.com/securely1g/sonic-bazel-registry/actions/runs/42094050308/job/127479337371)

Gazelle’s ARM Go test binaries use the same direct QEMU executor so a Go test
can execute itself again through the kernel’s ARM interpreter. Its shell-based
`go_proxy_test` uses the normal ARM runtime and its original mounts. All three
tests run with the published integration module. [ARM64 validation](https://github.com/securely1g/sonic-bazel-registry/actions/runs/42186480262/job/127787942313)


P4C `1.2.4.2.sonic.3` also runs on the Debian cross runners. Its build uses
native code generators, and its uncached package test uses the resulting ARM64
compiler to translate P4 source to BMv2. All five original build targets passed.
[Full ARM64 validation](https://github.com/securely1g/sonic-bazel-registry/actions/runs/42087404563/job/127456109251)

PI `0.1.3.sonic.3` also uses the Debian cross runners. Its runtime test builds
and runs a consumer of the installed ARM64 SDK and converts P4Info using the
installed tools. All four original builds and the uncached test passed.
[Full ARM64 validation](https://github.com/securely1g/sonic-bazel-registry/actions/runs/42180002707/job/127767164854)

The iproute2 6.15.0.sonic.7 cross route builds all four original targets and
executes both original tests. Its runtime test checks the package, and the
configure test invokes ARM GCC and recursive Make. The runner image needs the
PRoot fixes for guest GCC discovery and Linux exec argument limits. Roll out
that image before enabling this route in production.
[Qualified ARM job](https://github.com/securely1g/sonic-bazel-registry/actions/runs/42200862212/job/127848280179) · [Runner image change](https://github.com/securely1g/agi-projects/pull/92)

SWSS 0.0.3 selects its Sairedis and libteam dependencies directly. Its cross
job allows six hours for a cold serial C++ build and keeps the three original
runtime tests. [Historical cross-build and runtime tests](https://github.com/securely1g/sonic-bazel-registry/actions/runs/42238852494/job/127963546293)

Sairedis stages its declared ARM loader and libraries using the original test
wrappers. Its ASIC comparison and ZeroMQ signal fixtures run those wrappers
with native shell and Python, then execute the AArch64 payload through kernel
binfmt. The other five original tests use the ARM userspace executor.

Sairedis and SWSS registry jobs select the shared Cosmos 4.0.2 manifest by
module, version and execution architecture. Native AMD64, native ARM64 and
AMD64-to-ARM64 jobs receive the five pinned inputs, including both ARM loader
names, before Bazel starts. The shared reader fetches the official release
archive when needed, verifies every selected member against its locked SHA256,
and supplies the files through `--distdir`.
[Official release](https://github.com/jart/cosmopolitan/releases/tag/4.0.2)


The gawk smoke test uses gawk as a native execution tool while the direct gawk
build targets ARM64. Test execution follows the declared Bazel configuration;
the ARM cross fixture independently verifies native execution tools, ARM ELF
outputs and target Python compatibility. No test is replaced by a smaller smoke
test to make a module pass.

Inside a configured disposable runner with `/usr/local/bin/sonic-arm64`, use
fresh work and artifact directories. This command is a local opt-in example,
not a request to execute inside an active registered worker:

```sh
sudo -n /usr/bin/python3 -I -S ci/registry_ci.py run \
  --module libnl3 --version 3.7.0.sonic.7 --architecture arm64 \
  --cross-compile --test-executor /usr/local/bin/sonic-arm64 \
  --test-container-image "$SONIC_RUNNER_IMAGE_REFERENCE" \
  --bazel /usr/local/bin/bazel \
  --bazel-startup-arg=--host_jvm_args=-Xmx2g \
  --bazel-build-arg=--jobs=1 --bazel-build-arg=--discard_analysis_cache \
  --work-dir /tmp/registry-ci-libnl3-cross \
  --artifacts /tmp/registry-ci-libnl3-cross-artifacts
```

Cross mode creates explicit AMD64/Linux/Trixie execution and ARM64/Linux/Trixie
target platforms, retaining other constraints from the declared parents. This
also overrides host-derived aliases that would otherwise select AMD64 output
for an ARM64 request. Published Sonic Trixie platforms keep their toolchains only
when the exact graph-selected `sonic-build-infra` version is in
`cross_toolchain.py`'s verified registration allowlist. Its six immutable entries
declare AMD64 execution, ARM64 targets and Trixie; a familiar platform label or
newer version alone does not establish that capability. All other consumers,
including native-only infra 0.0.6 and SAI's 0.0.13, use a CI-local legacy C++
adapter compatible with the selected `rules_cc`. Both declared platform parents
remain inherited; the adapter's separate distribution constraint is additional.
The adapter uses the native-to-ARM GCC14.2 compiler and Trixie sysroot from
immutable `sonic-build-infra@0.0.25-34de7330abc72229dfc8dab88dec71b89c52aa88`.
The provider resolves separately and its JVM stops after preparation. Its
dependencies do not enter the consumer graph. Compiler/sysroot files are declared
action inputs, and the consumer's selected module versions must remain equal
before and after adaptation. Existing integration-module contents are preserved.
Evidence retains both graphs, provider lock and manifests, generated adapter and
platform definitions, declared/effective platform identities, and the selected
infra version and toolchain reuse decision. The registration allowlist is
source-level evidence; actual toolchain and runtime acceptance remain separate.

The selected-version check uses the complete module-only JSON from pinned
Bazel 8.5.1. Its [`mod graph` implementation](https://github.com/bazelbuild/bazel/blob/8.5.1/src/main/java/com/google/devtools/build/lib/bazel/commands/ModCommand.java)
also inspects every extension, including unused extensions. A failure solely in
that later inspection does not invalidate the already resolved module versions.
CI accepts only its exact exit-2 inspection diagnostic together with a complete,
unfiltered graph; every reference must have an expanded node. It retains the
original graph, stderr and `*-status.json`, marking extension inspection
incomplete. Resolution failures, malformed/truncated graphs and changed selected
versions still fail. The original build and test commands independently evaluate
all extensions they actually need; their failures are never suppressed.

The supplied executor runs unchanged ARM tests with QEMU user-mode and PRoot in
an ARM64 Trixie filesystem. This provides emulated userspace execution, not
native ARM hardware or kernel coverage. The helper probes the real guest CPU and
userspace before building, records the executor hash, and binds the work and
artifact paths plus container-local `/tmp`. An output base outside the work
directory is bound explicitly too. Native Bazel and build tools stay on AMD64.

Some existing test launchers embed exec-configured Python. For tests only, the
helper resolves the matching locked ARM standalone runtime, verifies real
ELF62/183 architectures and exact Python version/ABI, and passes complete-runtime
`--bind-at` mappings to the executor. Native interpreter files stay unchanged.
For simple shared-lock pip hubs, generated-consumer adapters select native wheels
for generators and ARM wheels for target tests, using the already selected
`rules_python` and original requirements bytes. Existing platform/index hubs and
development-only hubs remain unchanged; unsupported simple hub arguments or
changed module versions fail validation. Runtime mappings, hashes, original hub
configuration and lockfiles are retained in the cross receipts.

Cross builds may supply a readonly content-addressed Autoconf `CONFIG_SITE` that
recognizes an ARM compiler selected by a native build action. It preserves
explicit configure aliases, native compiler actions and caller-provided
`CONFIG_SITE`; it invents no cached target-probe answers. The effective site and
hash are retained. Source-owned runtime preparation executes through the guest
wrapper, preserving its locked inputs and checking an ARM receipt. Cross test
timeout defaults are 180/900/2700/7200 seconds for Bazel's four timeout classes;
explicit caller values and native defaults remain unchanged. All original build
and test labels, source checks and uncached-test requirements still apply.

The dedicated CI cross-fixture job runs all tests in `test_arm_cross_runtime.py`
with pinned native Bazel and the installed executor. Missing prerequisites or a
skipped cross test fail that job. Native unit jobs exclude this file explicitly,
so it is not counted twice or hidden among optional skips. For the same explicit
suite in a suitable disposable runner:

```sh
REGISTRY_CI_TEST_BAZEL=/usr/local/bin/bazel \
REGISTRY_CI_TEST_ARM_EXECUTOR=/usr/local/bin/sonic-arm64 \
  /usr/bin/python3 -I -S ci/run_runner_tests.py --suite cross
```

This foundation is not acceptance of the full ARM matrix. Before moving a module
row, validate its complete original build and uncached-test contract with the
native-generator/ARM-output foundation, unchanged source pins and resolution
receipts. SAI now selects the isolated provider, but
its full cross build and tests have not passed. Other known gaps include nested
Bazel/sandbox execution in rules_go, SWSS self-reexecution under emulation, and full libyang/protobuf
debugger/upstream coverage. P4C/PI source candidates and FIPS target-binutils work
remain separate module changes; transitive consumers retain their published
dependency pins. No source recipe or image change is included here.

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

### SONiC Go pseudo-version ordering

Registered SONiC patches may retain a Go pseudo-version suffix, for example
0.0.0.sonic.1-20200309174518-a00bece872fc. The planner accepts the exact
14-digit timestamp and 12-lowercase-hex form while preserving numeric release,
SONiC patch number and separator precedence. Equal release/patch snapshots
continue to use metadata registration order; hashes/timestamps are not sorted.
Malformed or unrelated suffixes remain rejected.
