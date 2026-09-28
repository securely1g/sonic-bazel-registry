# libyang-Python registry module

`3.1.0-sonic.4` supplies SONiC's patched upstream 3.1.0 binding for Common's
YANG schema generator. It selects
`sonic-build-infra 0.0.6-553b2f70f9ba77b74befdf77674894166139ddcc`, the merged
CPU hardening source needed for native AArch64.

The registry and fetched module declarations agree, and the external consumer
uses ordinary module resolution without a root override. The upstream archive,
four production patches, CFFI generator, binding targets and Python inputs are
unchanged. See the [version documentation](3.1.0-sonic.4/README.md) for the source
contract, public targets and native validation scope.

This proposal adds only `.4`. The superseded unmerged `.3` candidate and the
complete previous consumer snapshot remain byte-for-byte available at
`68838e5221c8e5211a41511a2bb37d0e5d217a93`, retained by the
[archive branch](https://github.com/securely1g/sonic-bazel-registry/tree/archive/pr9-before-candidate-cleanup-20260928).
Older archived `.1` and `.2` snapshots also remain available. No entry already on
registry main is removed or rewritten; the retained `.4` entry is unchanged.
