# Protobuf 3.21.12 runtime metadata for Trixie

Sysmgr's source targets in [buildimage PR #5](https://github.com/securely1g/sonic-buildimage/pull/5)
link `@sonic_protobuf//:libprotobuf`. Its planned
[`docker-sysmgr` consumer](https://github.com/securely1g/sonic-buildimage/issues/118)
needs that owner's runtime TAR and accurate package metadata for the installed
image. Image integration is separate; no image PR consumes this version yet.

The published `.1` entry builds unpatched upstream v21.12 and exports no package
metadata. This `.2` entry applies the complete Debian Trixie source patch series
for `3.21.12-11+deb13u1`, then the unchanged existing Bazel compatibility patch.
It reuses the existing shared-library, protoc, generated-message and runtime/debug
TAR targets. The new `//:runtime_packages.json` derives `libprotobuf32t64` control
fields from the original Debian control/changelog and the actual built TAR.
Standard metadata tools generate shared-library dependencies and t64 `Provides`;
no DEB package is built or new package recipe introduced.

The source archives come from the [official Debian source descriptor](https://deb.debian.org/debian/pool/main/p/protobuf/protobuf_3.21.12-11+deb13u1.dsc):

| Input | SHA-256 |
| --- | --- |
| `protobuf_3.21.12.orig.tar.gz` | `930c2c3b5ecc6c9c12615cf5ad93f1cd6e12d0aba862b572e076259970ac3a53` |
| `protobuf_3.21.12-11+deb13u1.debian.tar.xz` | `52c7c9377a2cb93649fb778baf4fe76d4489893ef04bad675acfa9b16e6313d5` |

All 32 Debian patches are retained in series order, followed by the unchanged
published Bazel patch. Their file boundaries and hunk offsets are normalized for
Bazel’s native patch parser; replaying them produces the same source bytes and
modes as the original Debian series. `debian-source.json` records original and
normalized hashes; authorship remains in the patch headers. The overlay's `sonic/debian` directory contains only
original control, changelog and copyright metadata; Debian's package-producing
rules are not copied or executed. Source and overlay integrity hashes are in
`source.json`. The existing SONAME and legacy copyright path are preserved;
the runtime adds the Debian copyright under `usr/share/doc/libprotobuf32t64`.

Presubmit retains the published native AMD64/ARM64 matrix and all seven original
build targets and three original tests. It adds the metadata output and extends
the installed-package test to verify its payload and recipe hashes, package
identity, architecture, generated dependencies and resolved t64 relationships.
This migration is exercised locally on native AMD64/Trixie; existing ARM64 CI
coverage remains in place without adding a new cross-compilation claim.
