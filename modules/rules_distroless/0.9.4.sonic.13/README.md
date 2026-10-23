# Lock import and real Debian installation

Buildimage #33 builds on #13's reviewed APT lock imports and installs those
original Debian archives with APT/dpkg. Version 0.9.4.sonic.13 composes registry
#111's lock-import support with #110's installer. It preserves both features,
including independent import namespaces, rather than reverting either parent.

The installer implementation is unchanged. Original-DEB aliases retain each
lock import's repository prefix and work in its payload-only path. Native
AMD64/ARM64 tests verify the original archive digest through two independent
imports, alongside all existing lock/header tests and installer unit tests.
They import existing Debian archives and do not create DEB packages. Actual
installed-image validation remains the consumer's responsibility.

Direct prerequisites are [registry #110](https://github.com/securely1g/sonic-bazel-registry/pull/110),
[#111](https://github.com/securely1g/sonic-bazel-registry/pull/111) and
[#123](https://github.com/securely1g/sonic-bazel-registry/pull/123). The supporting
base `codex/distroless-lock-install-candidate-prerequisites` combines the lock-import
and candidate-validation prerequisites. The installer composition and accounts
compatibility remain two distinct logical commits above that base. Consumer:
https://github.com/securely1g/sonic-buildimage/pull/33.

## Preserve base accounts alongside locked installation

This candidate also carries the public `accounts(base, architecture, users,
groups)` API from [registry #128](https://github.com/securely1g/sonic-bazel-registry/pull/128).
The #128 link records patch provenance: this recipe consumes the upstream 0.9.4
archive plus its local patches, without a #128 branch endpoint.
The simplified [infra #57](https://github.com/securely1g/sonic-build-infra/pull/57)
uses that API, and its package-metadata consumer in
[infra #58](https://github.com/securely1g/sonic-build-infra/pull/58) can be resolved
with this higher Distroless version by the Syncd image stack. Selecting `.sonic.13`
must retain the accounts behavior; a higher version alone does not supply it.

For example, adding a Redis user to a base containing `root` and `_apt` preserves
both inherited entries, adds Redis and its group, and rejects a conflicting UID.
The rule handles the actual OCI layer order and deletions, with plain, gzip, xz
and zstd layers. It emits an account layer and a receipt, using the existing
account writers, declared Python execution tools and BSD tar.

Patch `0016` preserves the reviewed account implementation and regression hunks
from #128. Its MODULE hunk adapts this candidate's existing Python dependency to
`rules_python@1.7.0` and Python 3.11, retaining the installer's `tar.bzl@0.10.4`.
All fifteen existing patches, overlays, six build targets and 26 existing tests
are unchanged. Five account test targets are added to both native architectures.
The locked-import implementation belongs to registry #111; the original infra
#59 patch header is retained as historical attribution with its unchanged bytes.
