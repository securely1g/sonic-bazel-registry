# Install Debian packages while retaining the published lock importer

`0.9.4.sonic.12` carries forward published `0.9.4.sonic.11` and adds optional
`apt_install` for [buildimage #33](https://github.com/securely1g/sonic-buildimage/pull/33).
The upstream 0.9.4 archive, patches `0002` through `0013`, compiler/header fixes,
locked imports and their regression tests are retained. Only the version patch
changes its identity; `0014-apt-install.patch` adds installation support.
The published `.sonic.11` entry remains unchanged.

For example, extracting `ca-certificates` files alone does not run its
configuration scripts. `apt_install` uses APT/dpkg in an isolated native Debian
filesystem to run those scripts and triggers, create the configuration and
certificate links, and maintain real package state. It outputs a configured
filesystem TAR and a receipt, not new Debian packages.

The installer consumes original `:deb` archives. If the same reviewed lock is
imported as `locked_import_ci` and `locked_import_ci_copy`, each import's
`libc6:deb` target resolves to its own prefixed repository and the exact hash
in the lock. The installation patch supplies these aliases without changing
the inherited lock-import patch.

Native AMD64/ARM64 presubmit retains all 25 published tests and six build targets,
adds the installer unit suite and original-DEB identity test, and extends the
independent archive test to check both lock prefixes. Full installed-image
behavior remains the consuming image's validation responsibility.

## Inherited locked APT imports

Published `0.9.4.sonic.11` provides all earlier compiler fixes and `apt.import_lock` for
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
entry=modules/rules_distroless/0.9.4.sonic.12
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
test results. Both native jobs must execute all 27 selected tests, including
the four locked-import regressions, fixture regeneration, installer unit tests and
original-DEB identity checks. Cross inspection
of ARM64 archives on AMD64 is not native ARM64 execution.
