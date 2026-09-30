# Shared SAI generator packages

This version registers [build-infra #8](https://github.com/securely1g/sonic-build-infra/pull/8)
at source commit `fe98da37f3c9ca525d58f60c4736347142be0c98`.
It adds Doxygen, Aspell, and English dictionaries to the existing `sysroot`
APT package set so SAI can use shared package resolution instead of its own
Debian lockfile and downloader. Debian snapshot dates, supported native CPUs,
and compiler directory labels remain unchanged by that source change.

The existing native AMD64/ARM64 registry consumer checks cover C/C++ compilation,
CPU hardening, linking, PIC, deployed contents, and matching debug packages.
[SAI #17](https://github.com/securely1g/sonic-bazel-registry/pull/17) validates the
new generator inputs by preparing dictionaries, running metadata generation,
and comparing its outputs with the retained sairedis baseline. Its consumer
selects the tool packages in the execution configuration.

The source archive and checksum identify the exact source commit. The only
production patch aligns its MODULE.bazel version with this registry entry;
overlays supply the existing infrastructure validation targets. Previously
published versions are preserved.
