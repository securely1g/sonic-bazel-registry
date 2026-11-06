# Compiler launcher with private linker arguments

This entry registers source commit
`f6da55505437cb139fdf610db8c61cb9420b0fec` from
[sonic-build-infra PR #82](https://github.com/securely1g/sonic-build-infra/pull/82).
The DASH Engine image build passed a 136,826-byte `LDFLAGS` value to the compiler,
exceeding Linux's per-string process limit before GCC could start.

The existing compiler launcher recognizes only its owner's private sibling
`.sonic-linker-arguments` vector, expands its ordered literal arguments and then
performs its existing per-working-directory library-path shortening. Ordinary
GCC response files remain opaque. The BMv2 producer change is tracked in
[registry PR #211](https://github.com/securely1g/sonic-bazel-registry/pull/211).

The source is based on maintained master `c47081689ed841191bf9531b46dad3430ed2e761`.
It includes the native interfaces previously backported onto
`0.0.26-51c838da6ff57295fde6e0bc3807841cb31a8568`, plus the maintained APT layer,
large system-include and shared tool fixes. That now-redundant interface patch
is removed; its existing 37 build and 43 test targets and every registry overlay
are retained. The source's own updated Libtool regression runs through the same
existing test label. The unchanged registry visibility patch remains applied.
Published versions and source recipes remain unchanged.

Retained validation from the original proposal covers the actual 338-argument Engine vector, real GCC14 C/C++
links, recursive Autoconf/Libtool builds and byte-identical short/long executables.
Registry native acceptance and the full Engine image rebuild remain pending.
This presubmit uses the existing tools-only kernel checks and produces no DEBs.
The consumer must select this exact version explicitly; commit suffix ordering
does not establish the intended source selection.

The combined image validation temporarily retains this candidate with
`rules_distroless` 0.9.4.sonic.16. Published infrastructure .27 and Distroless .17
require one shared APT lock; the current image and several component owners still
import independent reviewed locks. Keeping this tuple preserves those package
selections and the required linker fix while their lock migration remains
separate. Published .27 and BMv2 entries are unchanged.

PR #82 merged a rewritten replacement; this exact `f6da5550` snapshot is not in
maintained source history. Consumers therefore retain Draft status and an
explicit dependency on this temporary catalog. Reusing the candidate does not
establish new native image acceptance or completion of the shared-lock migration.
