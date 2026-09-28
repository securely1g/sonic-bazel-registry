# libyang-Python registry module

`3.1.0-sonic.4` provides SONiC's patched upstream 3.1.0 binding. It requests
`0.0.6-553b2f70f9ba77b74befdf77674894166139ddcc`, the merged infrastructure
commit containing the CPU hardening fix needed for native AArch64.
Common's YANG build therefore does not depend on unused feature compatibility or
separate linker and ELF-packaging changes.

This revision aligns the infrastructure dependency with the merged source
identity. The pre-merge and merged source trees are identical, so this is a
provenance update with no binding or toolchain behavior change. The previous
`3.1.0-sonic.3` entry remains in this registry with its exact original contents.
The upstream source archive, four production patches, binding targets, CFFI
source generator, and Python dependency inputs are unchanged.

Previous `.1` and `.2` entries existed only in PR snapshots and were never on
registry main. Their immutable snapshots remain available to pinned consumers:

- `.1`: `edae9085cdf07495d1e790a38ca5b080c526c461`,
  [archive branch](https://github.com/securely1g/sonic-bazel-registry/tree/archive/libyang-python-before-native-split-20260928).
- `.2`: `367c36162e75f55167d1875dc9c7bdab47bf2c1b`,
  [archive branch](https://github.com/securely1g/sonic-bazel-registry/tree/archive/libyang-python-before-cpu-only-20260928).

No main registry version is removed or rewritten. The new source declaration and
overlay declare the same `.4` version and updated infrastructure dependency;
standard Bazel module resolution selects that dependency without an override.
