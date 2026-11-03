# Reproducible SymCrypt provider build paths

Registers the maintained source revision
[`44d18af69f1b1868cebd41a93a76feb7c0b9a0f6`](https://github.com/securely1g/sonic-fips/commit/44d18af69f1b1868cebd41a93a76feb7c0b9a0f6),
containing the reviewed features from
[FIPS #9](https://github.com/securely1g/sonic-fips/pull/9),
[FIPS #10](https://github.com/securely1g/sonic-fips/pull/10), and
[FIPS #11](https://github.com/securely1g/sonic-fips/pull/11).
All three source PRs have merged. The complete Git tree matches the previously
accepted combined snapshot, including file modes; this registration now pins
the equivalent revision in maintained source history.
It replaces the sole unpublished candidate from
[registry #172](https://github.com/securely1g/sonic-bazel-registry/pull/172).
The published `0.0.3-d1a2c8f692d4197295269ed445022c3890b0f1a6` entry is unchanged.

The shared SWSS image in
[buildimage #136](https://github.com/securely1g/sonic-buildimage/pull/136)
inherits source-built Kerberos and OpenSSL from the config-engine base.
[FRR #137](https://github.com/securely1g/sonic-buildimage/pull/137) also uses
the OpenSSH client TAR in its debug image. Their local and CI builds exposed
absolute sandbox, sysroot and dependency paths in the installed debug files,
and a separate compiler-path string in OpenSSL's build information. These
differences also changed runtime build IDs and debug links.

The new source opts the Kerberos and OpenSSH foreign actions into upstream
`set_file_prefix_map = True`. OpenSSL already maps compiler debug paths; its
separate owner fix normalizes only the execution-root prefix in the compiler
information generated before compilation. Actual compiler arguments and
FIPS-linked outputs are not rewritten after linking. Existing source,
runtime/debug TAR, metadata and installation interfaces remain unchanged.

Two independent native AMD64 builds of the OpenSSL owner recompiled the
foreign action in different output/sandbox roots and produced identical
runtime, debug and SDK TARs. The actual generator has positive, changed-flag,
unset-environment and sibling-prefix controls. The installed OpenSSL test
checks the real compiler report. Kerberos and OpenSSH retain their existing
runtime, debug-link, Build ID and isolated GDB checks and now reject leaked
execution-root paths. These checks do not establish full-image reproducibility.

The SymCrypt provider and engine CMake builds previously embedded a build-tree
RPATH. Removing that path during installation left NUL padding in `.dynstr`
whose length depended on the build directory. The owner now disables CMake
RPATH generation for those two libraries. This avoids creating the unwanted
bytes while preserving their normal installed library dependencies. A private
test build disables action-cache reuse and compares each complete unstripped
ELF, including DWARF, from two fresh output bases of different lengths. The
helper uses Bazel batch mode so CI does not depend on reaping detached servers.
The installed package test still checks the original core test suite, rejection
of a corrupted integrity seal, provider and engine digests, and debug symbols.

This fix deliberately leaves the core's freshly generated integrity HMAC key
and generated assembly debug paths unchanged. It does not establish core,
runtime-TAR, or complete-image byte reproducibility.

This entry carries the previous published entry's complete native AMD64/ARM64
presubmit unchanged: all OpenSSL, Kerberos, OpenSSH and SymCrypt runtime/debug
outputs, package metadata, package tests and OpenSSL/SymCrypt integration.
The source CI separately runs the OpenSSL generator test and the new SymCrypt
provider/engine two-root reproducibility check on AMD64.
The only registry patch adapts the source's `0.0.3` module version to the
full source revision; the source archive and patched MODULE are verified.
No DEB producer is added or executed by this registration.

Commit suffixes are not chronological versions. This candidate's `44d18…`
suffix sorts below the published `d1a2…` suffix. Consumers must inspect the
resolved graph and align their requests, or use a root `single_version_override`
to select this exact candidate while validating it. Do not infer selection
from a direct `bazel_dep` alone. Normal registry defaults remain on maintained
`main`; Draft validation may replace that endpoint with this PR's reviewed
full registry commit.
