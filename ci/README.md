# Registry CI

Registry CI validates a module as a dependency in a fresh Bazel consumer. It
resolves the module from the proposed registry checkout, then builds the declared
outputs and runs explicit consumer and package tests. This exercises registry
resolution, archive integrity, patch and overlay application, compilation, and
the behavior covered by each module's tests.

The workflow runs on every pull request, pushes to `main`, and manual dispatches.
Pull requests select affected module versions. Changes to the CI implementation
or workflow run every configured version; pushes and manual runs do the same.
Changes to existing historical versions require a validation configuration too.
Unchanged historical entries without a configuration are not represented as
validated. Documentation-only changes can produce an empty module matrix.
In particular, `modules/<name>/README.md` does not select a version. A README
change alongside a new version still validates that new version.

`Registry CI` is the stable aggregate check intended for branch protection. It
passes only when planning and the runner's unit tests pass, and every selected
module job passes. A skipped module matrix is accepted only after successful
planning explicitly selected no jobs. Adding the workflow does not itself change
repository branch-protection settings.

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
- `build_targets`: required output labels, including runtime and matching debug
  packages where the module provides them.
- `test_targets`: explicit consumer and package test labels.
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

The fresh consumer ignores `MODULE.bazel.lock` and uses `--lockfile_mode=update`.
The generated resolution state is copied to artifacts, including after a failed
build when the file exists; it is never committed to the registry. Successful
validation requires that Bazel generated this evidence.

Use explicit labels for required outputs and tests. Wildcard builds can silently
skip targets incompatible with the selected platform. Add tests to the module's
source or registry overlay, and update the corresponding overlay integrity hashes
when changing overlay files. A successful library build alone does not establish
that downstream consumers can link it or that its runtime package works.

For libyang, CI builds the runtime and detached-symbol packages, then runs
`libyang_test` and `libyang_package_test`. These cover a dynamic consumer, YANG and
JSON parsing, PCRE2 pattern validation, the SONiC validation flag, extracted
runtime execution, SONAME and symlinks, runtime dependencies, and matching debug
symbols with GDB source-line lookup. This is focused module validation; the
downstream `sonic-swss-common` pipeline remains responsible for its integration
tests.

## Download build outputs

Open **Actions → Registry CI → a successful run → Artifacts** and download
`registry-ci-<module>-<version>-<architecture>` (`amd64` or `arm64`). Each artifact
contains `outputs.json`, mapping the manifest's required build targets to files
under `outputs/`, with their SHA256 hashes and sizes. Bazel's output paths are
preserved; use the index instead of relying on a configuration directory name.
Directory outputs, such as prepared YANG models, are indexed file by file.

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

## Environment and coverage

The build matrix uses native GitHub-hosted `ubuntu-24.04` and `ubuntu-24.04-arm`
servers with a `debian:trixie-20260918` container pinned to its multiarch image
digest. It installs the compiler and
package-test tools in the container and downloads Bazel 8.5.1 with a pinned SHA256
for the native CPU. GitHub actions are pinned to commit SHAs, checkout does not
persist credentials, and the workflow uses read-only repository permissions.

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
python3 ci/registry_ci.py plan --all --output /tmp/registry-ci-plan.json
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
`--all` with `--base <base-commit> --head <head-commit>`. Keep the work and artifact
directories outside the registry checkout and use a fresh work directory for a
clean reproduction.

See the [Bazel registry format](https://bazel.build/external/registry) for module
source, patch, and overlay metadata.
