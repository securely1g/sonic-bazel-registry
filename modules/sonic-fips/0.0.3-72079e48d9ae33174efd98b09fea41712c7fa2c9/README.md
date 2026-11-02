# Reproducible FIPS dependency build paths

Registers the combined source snapshot
[`72079e48d9ae33174efd98b09fea41712c7fa2c9`](https://github.com/securely1g/sonic-fips/commit/72079e48d9ae33174efd98b09fea41712c7fa2c9),
preserving the independent feature commits from
[FIPS #9](https://github.com/securely1g/sonic-fips/pull/9) and
[FIPS #10](https://github.com/securely1g/sonic-fips/pull/10).
Both source PRs are unmerged prerequisites. This registration stays Draft
until their reviewed changes are available from maintained source history.
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

This entry carries the previous published entry's complete native AMD64/ARM64
presubmit unchanged: all OpenSSL, Kerberos, OpenSSH and SymCrypt runtime/debug
outputs, package metadata, package tests and OpenSSL/SymCrypt integration.
The source CI separately runs the new OpenSSL generator test on AMD64.
The only registry patch adapts the source's `0.0.3` module version to the
full source revision; the source archive and patched MODULE are verified.
No DEB producer is added or executed by this registration.

Commit suffixes are not chronological versions. This candidate's `72079…`
suffix sorts below the published `d1a2…` suffix. Consumers must inspect the
resolved graph and align their requests, or use a root `single_version_override`
to select this exact candidate while validating it. Do not infer selection
from a direct `bazel_dep` alone. Normal registry defaults remain on maintained
`main`; Draft validation may replace that endpoint with this PR's reviewed
full registry commit.
