# Optional configured prebuild package-production gate

A module presubmit may set `"forbid_deb_outputs": true`. It is an opt-in safety
restriction, never an exemption from normal module or runner coverage. Existing
entries without the field execute exactly the existing path.

After consumer root/source patch/toolchain preparation and before the first
Bazel build, query the union of **all architecture-selected build and test
labels**, using the same actual registry/target/host/tool flags. Retain cquery
files and the transitive aquery JSON separately from stderr, plus commands and
an audit receipt with graph hash. Each query has a1200-second timeout. Empty,
malformed, incomplete-reference or failed query output cannot pass. Legal labels
such as Common++ are quoted with JSON encoding.

Reject any selected action output ending .deb/.udeb and DEB mnemonics except the
existing import/extraction/runtime-metadata exceptions. Debian package imports
are not package production. This is a declared-action/output guard, not a
universal filesystem-side-effect sandbox. It does not execute build/test actions
or authorize previously restricted fixtures. Repository evaluation/toolchain
preparation still has its ordinary declared side effects and scope.

The full graph may be large and is retained for audit/upload; current relay
AMD64 evidence is approximately310MB and36,565 actions. Memory/storage use is
not claimed bounded by the query deadline. A nativeARM graph remains a separate
required execution, not inferred from AMD64. No test target count/case/PASS is
implied by configuration success.

This generic code must be reviewed/integrated separately from a module-only
registration. The new field is rejected by an older validator, so a module must
not opt in publicly before accepted support is available. A shared-helper PR
still triggers full normal consumer coverage; no planner/path exemptions are
introduced. Local preparation is not publication or dispatch permission.
