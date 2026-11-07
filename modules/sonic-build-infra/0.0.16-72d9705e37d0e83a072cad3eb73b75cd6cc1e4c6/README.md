# Debian GCC toolchains and shared-library runtime lookup

This registers build-infrastructure source `72d9705e37d0e83a072cad3eb73b75cd6cc1e4c6` from
[the runtime-library search fix](https://github.com/securely1g/sonic-build-infra/pull/50), based on the Debian GCC
toolchains merged in [build-infra #49](https://github.com/securely1g/sonic-build-infra/pull/49).
The source restores the linker RPATH behavior required by transitive shared
libraries. This candidate consumes an unmerged source fix and remains Draft.

Registry CI imports the module into a fresh Bazel 8.5.1 consumer on native
AMD64 and ARM64. Existing compiler, configure/Make, Kerberos, shared-library,
and runtime/debug TAR checks remain selected. The new transitive runtime test
checks that an executable can load a shared library and its indirect library.
The selected targets do not produce DEB packages. Native CI results are tracked
on this PR; registry CI does not claim cross execution.

Consumers should request `0.0.16-72d9705e37d0e83a072cad3eb73b75cd6cc1e4c6`. Commit suffixes do not sort by source date;
use a root `single_version_override` when another dependency requests a
lexically higher snapshot. Check the selected graph and fetched MODULE after
updating pins. The normal registry endpoint remains maintained `main`; Draft
validation selects the reviewed candidate through its explicit CI mechanism.
