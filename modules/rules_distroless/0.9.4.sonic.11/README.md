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
The registry runs all twenty retained tests and four new regressions on native
AMD64 and ARM64. The new tests check graph integrity, locked package metadata,
complete dependencies, architecture-independent packages and identical archive
contents across isolated imports. No DEBs are produced.

See [patch provenance and validation](PATCHES.md).

## Refresh the reviewed lock fixture

Keep the Lua/netbase roots and their complete AMD64/ARM64 closures from a
reviewed image lock. From this registry checkout, run:

```sh
entry=modules/rules_distroless/0.9.4.sonic.11
python3 "$entry/tools/select_lock_fixture.py" \
  --input /path/to/sonic-buildimage/dockers/docker-base-trixie/bazel/apt.lock.json \
  --output "$entry/overlay/registry_ci/locked_import/apt.lock.json"
```

Review the archive URLs, hashes, package versions and closure changes before
updating the fixture's overlay integrity in `source.json`. The helper only
selects existing Debian archive metadata; it does not produce DEBs or resolve
new packages. Passing the checked-in fixture as `--input` regenerates identical
bytes and is checked in each native validation job.

`validate_native.py` runs the existing registry validation for this version.
It verifies both the native Linux host and Debian userspace architecture,
regenerates the fixture without changing it, and checks that every file in this
recipe remains unchanged after validation. Its `locked-import-validation.json`
receipt accompanies the generic runner's generated lock, input declarations and
uncached test results. Both native jobs must execute all four locked-import
regressions, alongside the twenty retained Distroless tests. Cross inspection
of ARM64 archives on AMD64 is not native ARM64 execution.
