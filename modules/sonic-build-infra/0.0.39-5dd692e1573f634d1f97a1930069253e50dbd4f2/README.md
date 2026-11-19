# Temporary wheel metadata consumer validation

This unpublished snapshot selects source commit `5dd692e1573f634d1f97a1930069253e50dbd4f2` from
`securely1g/sonic-build-infra:codex/wheel-runtime-metadata-dhcp`. It is used only
by the DHCP image validation branch; it is not part of registry PR #235.

The source-owned adapter extends installed wheel metadata with the generated
runtime package plan. This entry uses the actual owner base version 0.0.39 and
an identity-only generated MODULE overlay. Published 814761 inputs are unchanged.
Because 5dd692 sorts below 814761, candidate consumers must explicitly select
this version using a matching `single_version_override`; otherwise MVS may
retain the older implementation requested by another source owner.

Selected AMD64 validation builds only the wheel runtime TAR, distribution
metadata and runtime plan, and runs `//python:wheel_layer_test` and
`//python/tests:wheel_runtime_test`. No kernel package, DEB fixture or DEB target
is selected. The source agent audited 334 configured actions and passed both
selected tests. The separate registry consumer action graph also passed its
no-DEB audit (334 configured actions, zero actions executed). Exact-head
native consumer acceptance remains pending; analysis is not a build/test result.

Archive SHA256: `056b40a114a1ef7451e247e199c33678b2c8756b725a02830553b98c6cde247b`. All 506 tracked source blobs, Git file
types and executable bits match the published owner commit. No source patch
or private runtime/package implementation is introduced by this entry.
