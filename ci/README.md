# Registry CI

The [registry workflow](../.github/workflows/registry-ci.yml) checks publication policy, tests the CI runner, and starts a [module job](../.github/workflows/registry-module.yml) for each selected module version and architecture. It was ported from [the securely1g registry CI](https://github.com/securely1g/sonic-bazel-registry/tree/884f1ab596d7efd58b56939d5abd62c6aff1f3a8/ci).

## Which versions run

A pull request validates the affected registrations against the maintained `main` branch. A change to shared CI or registry configuration selects the latest eligible version of every module that has a presubmit recipe. Pushes to `main` and ordinary manual runs select the latest eligible versions. Select `all_versions` on a manual run to include every configured historical version.

The planner lists existing versions without a `presubmit.json` in the plan log. Those versions have no module build or test result. On the initial upstream baseline, all 17 published versions across seven modules are in that category. A contributor can add a recipe to a published version. CI requires each new registration to provide a recipe and protects published source inputs against modification. Both the candidate and already-published versions must remain consistent with the module's `metadata.json`.

## What a module job checks

Place `presubmit.json` in `modules/<module>/<version>/`. Declare the supported architectures, platform labels, build targets and test targets. An `integration_test_module` can point to a consumer fixture under the same entry to exercise an API as a downstream project would. The [pinned recipe reference](https://github.com/securely1g/sonic-bazel-registry/blob/884f1ab596d7efd58b56939d5abd62c6aff1f3a8/ci/README.md#module-configuration) describes the optional toolchains, consumer dependencies, packaging checks and artifact settings.

The runner creates a fresh consumer, resolves against the checkout and the Bazel Central Registry, builds the declared outputs and runs the declared tests uncached. It checks that the fetched module declaration agrees with the registry and verifies that the registered source inputs remain unchanged. Each module job uploads its build and test logs, Bazel events and available receipts. A successful run includes `validation.json`, the resolution lock and test results. The planner uploads `registry-ci-plan` with the selected matrix and its log.

## Execution environments

Pull requests run on GitHub-hosted `ubuntu-24.04` and `ubuntu-24.04-arm` runners. The module jobs run natively in the pinned Debian Trixie container with Bazel 8.5.1. The native harness tests run directly on the Ubuntu hosts. The default requires public source access and no private runner, mirror, credential or cache. The [download configuration](source_mirrors.cfg) provides exact-URL alternatives for known artifacts. Bazel verifies downloads against the original integrity lock.

Maintainers can set the repository variable `REGISTRY_RUNNER_MODE=cross` for pushes and manual dispatches on canonical `main` after provisioning the labeled AMD64 Trixie workers and ARM executor. Configure runner-group access restrictions and isolation before exposing a self-hosted pool to a public repository. Contributors can edit workflow code in a pull request, so the workflow's branch condition alone cannot enforce runner-group access. Cross mode also needs the exact `sonic-build-infra` provider in [cross_toolchain.py](cross_toolchain.py) to be published to this registry. The initial upstream registry does not have that version. The private Debian mirror and download audit integrations are optional for provisioned workers.

## Reproduce a run

Check out the head being validated. The following assumes `upstream` points to `sonic-net/sonic-bazel-registry`.

```sh
git fetch upstream main
python3 ci/registry_ci.py plan --published "$(git rev-parse upstream/main)" \
  --base "$(git merge-base HEAD upstream/main)" --head "$(git rev-parse HEAD)" \
  --output /tmp/registry-ci-plan.json
python3 ci/run_runner_tests.py --suite native
```

Set `REGISTRY_CI_TEST_BAZEL` to an absolute Bazel 8.5.1 executable to run the Bazel-backed harness tests. Set `REGISTRY_CI_TEST_MIRROR_ONLY=1` to explicitly test the ARM archive and gawk fallback hosts from an empty cache. To reproduce a module job, use a matching native Trixie environment, select a row printed in the plan and give the runner fresh directories outside the checkout. For example, for a candidate registering `rules_python@1.9.0.sonic.1` on AMD64, run

```sh
python3 ci/registry_ci.py run --module rules_python --version 1.9.0.sonic.1 \
  --architecture amd64 --bazel /usr/local/bin/bazel \
  --work-dir /tmp/registry-rules-python-amd64-work \
  --artifacts /tmp/registry-rules-python-amd64-artifacts
```
