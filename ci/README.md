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
- `build_flags` (optional): module-qualified Starlark settings applied to both
  builds and tests, for example
  `--@sonic-swss-common//tools/bazel:yang_modules=False`. Each setting must belong to
  the module under test and include its value. Native Bazel options, duplicate
  settings, and options that redirect registries or override test execution are
  rejected. The selected flags are retained in `validation.json`.
- `execution_images` (optional): a digest-pinned build-tools container and its
  recipe SHA256 for every declared architecture; see below. Omission retains the
  default Debian setup.

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
to an older source revision. Source, patch, and registry replacements are not
supported. Dependencies used by the test environment must actually be fetched;
the runner fails if a declared dependency is missing or its fetched module name
or version differs. An empty `consumer_deps` list adds no pins.

Artifacts retain the generated `consumer.MODULE.bazel`, `MODULE.bazel.lock`, each fetched dependency's
`consumer-dep-<name>.MODULE.bazel`, and the declared `consumer_deps` in
`validation.json`. These pins apply only to this CI test project. Downstream
repositories such as `sonic-swss-common` remain responsible for validating their
own dependency selection and integration builds.

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
servers. By default, jobs use a `debian:trixie-20260918` container pinned to its
multiarch image digest. They install the compiler and
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

### Pinned build-tools containers

A module whose generators need installed tools can select an immutable execution
image in `presubmit.json`. Each architecture needs an entry with exactly `image`
and `recipe`; both entries may use the same multiarch index digest. This example
shows the shape only; replace both digest placeholders with verified SHA256s:

```json
"execution_images": {
  "amd64": {
    "image": "ghcr.io/securely1g/sonic-build-tools@sha256:<image-digest>",
    "recipe": "<recipe-sha256>"
  },
  "arm64": {
    "image": "ghcr.io/securely1g/sonic-build-tools@sha256:<image-digest>",
    "recipe": "<recipe-sha256>"
  }
}
```

The image reference must include its registry hostname and a lowercase SHA256
digest, without a tag, credentials, or container options. It must be publicly
pullable. The workflow runs that exact reference and skips APT installation and
the Bazel download. The image must already supply the tools listed under local
reproduction, Bash, and Bazel 8.5.1. Adding an image does not grant the workflow
package-write permissions or registry credentials.

Before creating a consumer or running a build, the runner checks native CPU
architecture, Bazel's version, the exact configured `--execution-image` argument,
and `/etc/sonic-build-tools.json`. That marker must contain `schema_version: 1`,
the selected `architecture`, and `recipe_sha256` matching the manifest. Additional
marker fields, such as installed package versions, are retained. The recipe is
the image producer's hash of its build inputs; it is distinct from the OCI image
digest. Changing installed tools requires rebuilding and selecting a new image
digest, even if rebuilding the same recipe.

The container runtime enforces the image digest. The marker verifies the expected
recipe and architecture; it is not an independent cryptographic attestation of
the running filesystem. Supplying an image argument outside its container does
not reproduce the environment. Review the image's source and provenance before
selecting it, and do not modify its tools during validation.

The runner passes `SONIC_BUILD_TOOLS_IMAGE` and `SONIC_BUILD_TOOLS_RECIPE` as
explicit `--action_env`, `--host_action_env`, and `--test_env` values, so actions
using Bazel's default action environment (including execution-configuration
tools) and tests include this identity in their cache inputs.
Custom actions that use their own environment must also include the image
identity in their declared arguments, environment, or execution properties;
`--action_env` alone cannot make such an action container-aware. Selecting a CI
container does not configure a remote executor or change a compiler's target
sysroot.

`execution-environment.json` retains the verified image, recipe, full marker,
and Bazel version before the build starts. Successful `validation.json` also
includes that record. Setup rejection remains visible in the Actions job log.

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

For an entry with `execution_images`, run the same command inside the selected
container on the matching native host and pass its exact reference. For example,
after replacing the values below with the entry's module, version, and image:

```sh
image='ghcr.io/securely1g/sonic-build-tools@sha256:<image-digest>'
mkdir -p /tmp/registry-ci-container-artifacts
docker run --rm --platform linux/amd64 \
  -v "$PWD:/registry:ro" \
  -v /tmp/registry-ci-container-artifacts:/artifacts \
  "$image" python3 /registry/ci/registry_ci.py run \
  --module MODULE --version VERSION --architecture amd64 \
  --execution-image "$image" \
  --work-dir /tmp/registry-ci --artifacts /artifacts
```

Use a native ARM64 host with `linux/arm64` and `--architecture arm64` for the
other matrix entry. Emulation is not evidence of native ARM64 coverage.

See the [Bazel registry format](https://bazel.build/external/registry) for module
source, patch, and overlay metadata.
