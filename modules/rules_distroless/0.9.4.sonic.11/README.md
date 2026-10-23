# Import one reviewed APT lock and preserve base accounts

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
The registry retains the twenty earlier tests and four locked-import regressions
on native AMD64 and ARM64. The locked-import tests check graph integrity, locked package metadata,
complete dependencies, architecture-independent packages and identical archive
contents across isolated imports. No DEBs are produced.

The archive integration test lives in the independent Bazel module at
[`tests/integration`](tests/integration). Its `MODULE.bazel` declares the
dependency and sample lock imports, and its `BUILD.bazel` exposes
`//:archive_contract_test`. CI copies this module to a fresh work directory and
runs that test alongside the twenty retained tests and three locked-import unit
tests in the registry-fetched dependency. The test module and fixture are not
overlaid into the dependency, and no test-only patch changes its MODULE file.

## Add service accounts without replacing the base's users

This unreleased candidate also exposes the public `accounts` rule submitted in
[upstream PR #290](https://github.com/bazel-contrib/rules_distroless/pull/290),
referencing [issue #278](https://github.com/bazel-contrib/rules_distroless/issues/278).
For example, a base containing `root` and `_apt` gains `redis` while keeping both
inherited records. The same operation adds the Redis group and checks that new
users have valid primary groups and that names and numeric IDs do not conflict.

```starlark
load("@rules_distroless//distroless:defs.bzl", "accounts")

accounts(
    name = "accounts",
    base = ":base",
    architecture = "amd64",
    users = [{"username": "redis", "password": "x", "uid": 100, "gid": 101,
              "home": "/var/lib/redis", "shell": "/usr/sbin/nologin"}],
    groups = [{"name": "redis", "password": "x", "gid": 101}],
)
```

Add `:accounts` to the child image's `oci_image.tars` using the same base.
`:accounts.receipt` records the base digest and account-file hashes. The rule
uses declared Python and BSD tar execution tools, preserves inherited file bytes,
and respects newer layers and OCI deletion markers. It does not create home
directories, configure packages or update password databases. Existing standalone
`passwd` and `group` rules retain their behavior.

[Build-infra #57](https://github.com/securely1g/sonic-build-infra/pull/57) consumes
this API in place of its own merge implementation. This registry entry owns the
temporary backport and runs the five upstream account-test targets: the unit
suite plus public-rule checks for uncompressed, gzip, xz and zstd base layers.
Keep the patch until an upstream release containing the feature is selected and
the same tests pass on native AMD64 and ARM64.

See [patch provenance and validation](PATCHES.md).

## Refresh the reviewed lock fixture

Keep the Lua/netbase roots and their complete AMD64/ARM64 closures from a
reviewed image lock. From this registry checkout, run:

```sh
entry=modules/rules_distroless/0.9.4.sonic.11
python3 "$entry/tools/select_lock_fixture.py" \
  --input /path/to/sonic-buildimage/dockers/docker-base-trixie/bazel/apt.lock.json \
  --output "$entry/tests/integration/apt.lock.json"
```

Review the archive URLs, hashes, package versions and closure changes before
committing the updated fixture. Each package's locked SHA256 is verified when
Bazel fetches its archive. The helper only
selects existing Debian archive metadata; it does not produce DEBs or resolve
new packages. Passing the checked-in fixture as `--input` regenerates identical
bytes and is checked in each native validation job.

`validate_native.py` runs the existing registry validation for this version.
It verifies both the native Linux host and Debian userspace architecture,
regenerates the fixture without changing it, and checks that every file in this
recipe, including the integration module, remains unchanged after validation.
Its `locked-import-validation.json`
receipt accompanies the generic runner's generated lock, input declarations and
uncached test results. Both native jobs must execute all four locked-import
regressions, alongside the twenty retained Distroless tests and five account
tests. Cross inspection
of ARM64 archives on AMD64 is not native ARM64 execution.
