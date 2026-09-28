# libyang-Python registry module

`3.1.0-sonic.3` provides SONiC's patched upstream 3.1.0 binding. It requests
`0.0.6-7ffcef1849fb7c96ef99f5d64339b87eac0beefd`, which is current
infrastructure master plus the CPU hardening fix needed for native AArch64.
Common's YANG build therefore does not depend on unused feature compatibility or
separate linker and ELF-packaging changes.

This revision changes the infrastructure dependency from `3.1.0-sonic.2`.
The upstream source archive, four production patches, binding targets, CFFI
source generator, and Python dependency inputs are unchanged.

Previous `.1` and `.2` entries existed only in PR snapshots and were never on
registry main. Their immutable snapshots remain available to pinned consumers:

- `.1`: `edae9085cdf07495d1e790a38ca5b080c526c461`,
  [archive branch](https://github.com/securely1g/sonic-bazel-registry/tree/archive/libyang-python-before-native-split-20260928).
- `.2`: `367c36162e75f55167d1875dc9c7bdab47bf2c1b`,
  [archive branch](https://github.com/securely1g/sonic-bazel-registry/tree/archive/libyang-python-before-cpu-only-20260928).

No main registry version is removed or rewritten. The new source declaration and
overlay declare the same `.3` version and updated infrastructure dependency;
standard Bazel module resolution selects that dependency without an override.
