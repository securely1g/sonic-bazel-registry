# Temporary wheel metadata consumer validation

This unpublished snapshot selects source commit `6f32af5649f08819bf97499e8a0c5435a161f0ef` from
`securely1g/sonic-build-infra:codex/wheel-runtime-metadata-dhcp`. It replaces the
previous temporary snapshot on the DHCP image validation branch; it is not part
of registry PR #235.

The source-owned adapter extends installed wheel metadata with the generated
runtime package plan. It also accepts rules_python's exact patched-wheel filename
convention while retaining the installed METADATA version and rejecting other
name, version, tag and RECORD mismatches. Raw wheel and metadata hashes remain
bound to the installed output. This entry uses the actual owner base version
0.0.39 and an identity-only generated MODULE overlay. Published 814761 inputs
are unchanged. Because 6f32af sorts below 814761, candidate consumers explicitly
select this version using a matching `single_version_override`; otherwise MVS
may retain the older implementation requested by another source owner.

Selected AMD64 validation builds only the wheel runtime TAR, distribution
metadata and runtime plan, and runs `//python:wheel_layer_test` and
`//python/tests:wheel_runtime_test`. No kernel package, DEB fixture or DEB target
is selected. The source validation passed 32 unit tests and both selected Bazel
tests. All 33 existing Config Engine wheel inputs passed metadata/RECORD
validation; installing the actual patched Redis wheel twice preserved its
payload, installed metadata and deterministic output. Exact-head registry
consumer acceptance remains pending; owner tests are not registry acceptance.

Archive SHA256: `1b4ba9b23b36093bce2671b7f399fcfca331082d282d29bb94b0583a03ea06bd`. All 506 tracked source blobs, Git file
types and executable bits match the published owner commit. No source patch
or private runtime/package implementation is introduced by this entry.
