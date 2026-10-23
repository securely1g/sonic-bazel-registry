# Import one reviewed APT lock

This version retains all `0.9.4.sonic.10` fixes and adds `apt.import_lock` for
container package inputs. It replaces a second MODULE file repeating every
package version already recorded in the lock.

```starlark
apt = use_extension("@rules_distroless//apt:extensions.bzl", "apt")
apt.import_lock(lock = "//image:apt.lock.json")
use_repo(apt, "image_packages")  # dependency-set name in the lock
```

The extension reads the lock's exact archive URLs and SHA256 digests without
resolving package indexes or rewriting the input. Every root and transitive
package exposes independent `:data` and `:control` targets, plus its package
closure. The existing Distroless importer and archive preparation rule are reused.
Native C++ imports continue to use `apt.install`, whose Contents indexes are
not present in runtime locks.

This registry module owns the implementation, regression tests and fixture
regeneration helper. [Build-infra #59](https://github.com/securely1g/sonic-build-infra/pull/59)
is the original proposal, superseded by this registry implementation; it is not
a source dependency.
The registry runs all twenty retained tests, four locked-import regressions and
a fixture-regeneration test on native AMD64 and ARM64. The tests check graph
integrity, locked package metadata, complete dependencies,
architecture-independent packages and identical archive contents across
isolated imports. No DEBs are produced.

The archive integration test lives in the independent Bazel module at
[`tests/integration`](tests/integration). Its `MODULE.bazel` declares the
dependency and sample lock imports, and its `BUILD.bazel` exposes
`//:archive_contract_test` and `//:fixture_regeneration_test`. CI copies this
module to a fresh work directory and runs both tests alongside the twenty
retained tests and three locked-import unit tests in the registry-fetched
dependency. The test module and fixture are not
overlaid into the dependency, and no test-only patch changes its MODULE file.

See [patch provenance and validation](PATCHES.md).

## Refresh the reviewed lock fixture

Keep the Lua/netbase roots and their complete AMD64/ARM64 closures from a
reviewed image lock. From this registry checkout, run:

```sh
entry=modules/rules_distroless/0.9.4.sonic.11
python3 "$entry/tests/integration/tools/select_lock_fixture.py" \
  --input /path/to/sonic-buildimage/dockers/docker-base-trixie/bazel/apt.lock.json \
  --output "$entry/tests/integration/apt.lock.json"
```

Review the archive URLs, hashes, package versions and closure changes before
committing the updated fixture. Each package's locked SHA256 is verified when
Bazel fetches its archive. The helper only
selects existing Debian archive metadata; it does not produce DEBs or resolve
new packages. Passing the checked-in fixture as `--input` regenerates identical
bytes. The ordinary Bazel `fixture_regeneration_test` invokes that helper with
declared inputs and writes its comparison copy to a temporary test directory.

The shared registry runner validates every module through the same CI entry
point. It checks the native Linux host and Debian userspace architecture and
verifies that recipe inputs remain unchanged, including after a failed build.
It retains the generated lock, input declarations, source hashes and uncached
test results. Both native jobs must execute all 25 selected tests, including
the four locked-import regressions and fixture regeneration. Cross inspection
of ARM64 archives on AMD64 is not native ARM64 execution.
