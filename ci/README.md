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
