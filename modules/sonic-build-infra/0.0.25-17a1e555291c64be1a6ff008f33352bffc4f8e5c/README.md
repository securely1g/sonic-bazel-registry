# Native component build and OCI TAR interfaces

This entry keeps the published `17a1e555291c64be1a6ff008f33352bffc4f8e5c`
source archive, integrity and module version. Patch `0003` backports the reviewed
native implementation from [build-infra #67](https://github.com/securely1g/sonic-build-infra/pull/67),
source `1341eaf4a7759ef0121ae7c17edcd0000d063038`, for
[FRR](https://github.com/securely1g/sonic-buildimage/pull/51) and
[libteam](https://github.com/securely1g/sonic-buildimage/pull/61).
The original version and cross-test visibility patches remain byte-identical.
This is an explicitly requested update to the existing version, not a new release.

The backport adds native compilation/runtime helpers, matching runtime/debug
TARs, and one shared Bookworm execution-tool set with separate Perl and
Valgrind/Tcl subsets. Bookworm retains GCC 12 and glibc 2.36; Trixie tools
remain separate. The source-receipt fix from
[build-infra #69](https://github.com/securely1g/sonic-build-infra/pull/69)
remains intact: optional paths may be omitted only for validated source receipts.

Validation retains all 32 build targets and 40 tests on native AMD64 and ARM64,
including real-ELF ORIGIN/RPATH/RUNPATH lookup, installation links, checked
receipts, TAR ownership, Perl generation and Bookworm instrumentation. The
registry prefix-map fixture checks the external source's execpath, debug
compilation directory, source filename and `__FILE__` separately.

The patched module requires the native APT exports from
[registry #146](https://github.com/securely1g/sonic-bazel-registry/pull/146)
in `rules_distroless 0.9.4.sonic.13`. Keep dependent PRs in Draft while this
reviewed registry update remains unlanded; normal registry defaults stay on `main`.
