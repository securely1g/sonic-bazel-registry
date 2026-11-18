# Common source installation controls and locked Rust source

This entry registers the ordinary source merge
`2a4ddd070edb719f2e969a880a5cfff711e64e72` from
[sonic-swss-common #48](https://github.com/securely1g/sonic-swss-common/pull/48).
Its numeric base remains the source MODULE version, `0.0.8`. The sole patch
aligns that identity with the full commit-qualified registry version. Runtime,
control generation and Rust implementations remain in the source repository.

The source exports the original fixed `4b86a770` Rust crate through
`//crates/swss-common:locked_source.bzl` for caller-owned dependencies. Its
existing runtime metadata producer retains the original `dh_makeshlibs`,
`dh_installdeb` and `debian/conffiles` contract, including generated shlibs,
the ldconfig trigger and default symbols. Consumers reuse the existing native,
Python and CLI installation targets and `//:runtime_packages.json`.

Presubmit retains the published predecessor's 16 build targets and 24 tests,
and adds the source's independent locked-Rust caller test. Root dependency
pins match the actual merged source's validated infrastructure graph rather
than the unrelated dependency-refresh branch. The runtime-preparation helper
is pinned by its actual source digest. Native architectures remain AMD64 and
ARM64; local validation and hosted results are recorded separately.

This source-based version sorts below the old numeric `0.0.9`; consumers must
select the reviewed version explicitly, using their existing standard
`single_version_override` where a higher transitive request exists. Commit
hashes are not dates for minimum-version selection.

After registration, BMP, host-services and the buildimage root must replace
their development Common references with this real registered version. The
existing VS root override can select it without a new mechanism. Source CI,
registry-fetch validation, consumer integration and full VS acceptance remain
separate evidence.
