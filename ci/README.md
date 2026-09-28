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
  each with `name`, `version`, and optional `repo_name`.
- `platforms`: an explicit Bazel target platform label for each architecture.
- `build_targets`: required output labels, including runtime and matching debug
  packages where the module provides them.
- `test_targets`: explicit consumer and package test labels.
- `build_flags` (optional): module-qualified Starlark settings applied to both
  builds and tests, for example
  `--@sonic-swss-common//tools/bazel:yang_modules=False`. Each setting must belong to
  the module under test and include its value. Native Bazel options, duplicate
  settings, and options that redirect registries or override test execution are
  rejected. The selected flags are retained in `validation.json`.
- `version_overrides` (optional): a map from module names to exact versions for
  the tested module or explicit `consumer_deps`. The consumer emits version-only
  `single_version_override` declarations; source, patch, and registry overrides
  are not supported. This handles commit-suffixed versions whose lexical order
  differs from the required source revision. An override for the tested module
  must retain its tested version. The runner verifies fetched module identities
  and retains the requested versions and fetched declarations as artifacts.

For example, a consumer depending on `sonic-build-infra` can select a specific
registered source revision even when another dependency requests a lexically
higher historical version:

```json
"version_overrides": {
  "sonic-build-infra": "0.0.4-7ce718859ccf79fdafbf5cb5abd32bcca164f126"
}
```

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
