# libyang-Python registry module

`3.1.0-sonic.1` is the first proposed registry revision of SONiC's patched
upstream 3.1.0 binding for Common's YANG schema generator. It selects
`sonic-build-infra 0.0.6-553b2f70f9ba77b74befdf77674894166139ddcc`, the merged
CPU hardening source needed for native AArch64.

The registry and fetched module declarations agree, and the external consumer
uses ordinary module resolution without a root override. See the
[version documentation](3.1.0-sonic.1/README.md) for the production source,
four-patch series, public targets and native validation scope.

This proposal adds one version. Earlier draft revisions remain available through
their immutable registry snapshots. The previous `.4` consumer snapshot,
`bb8fafef895caa784ad4019c052e10cbc1d7148b`, is retained by the
[pre-rename archive](https://github.com/securely1g/sonic-bazel-registry/tree/archive/pr9-before-first-revision-20260929).
Renumbering the candidate changes its module declarations and the corresponding
overlay integrity; its source archive, production patches, build definitions and
dependencies remain unchanged. Entries already on registry main are unchanged.
