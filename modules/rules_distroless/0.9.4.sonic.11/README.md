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

The implementation and archive regression tests are maintained in
[build-infra #59](https://github.com/securely1g/sonic-build-infra/pull/59).
The registry runs all twenty retained tests and four new regressions on native
AMD64 and ARM64. The new tests check graph integrity, locked package metadata,
complete dependencies, architecture-independent packages and identical archive
contents across isolated imports. No DEBs are produced.

See [patch provenance and validation](PATCHES.md).
