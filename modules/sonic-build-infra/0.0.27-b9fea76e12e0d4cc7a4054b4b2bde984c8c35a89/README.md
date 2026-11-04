# Locked native migration interfaces, including Bookworm

This registration uses landed source commit `b9fea76e12e0d4cc7a4054b4b2bde984c8c35a89` from
[build-infra #79](https://github.com/securely1g/sonic-build-infra/pull/79) as
`0.0.27-b9fea76e12e0d4cc7a4054b4b2bde984c8c35a89`. The source retains published native migration interfaces and
uses the canonical APT lock for Bookworm toolchains, build tools and target
debug files on AMD64 and ARM64. Individual header and library exports remain
available, including the Perl embedding headers and shared library.

The source archive is pinned to the public `securely1g/sonic-build-infra`
commit. Its checksum is calculated from downloaded codeload bytes, with every
file and Git executable/symlink mode compared against that exact source tree.
The pin is the merge commit on the maintained source branch, including the
source PR changes and their final published provenance.
Normal source and registry defaults use the maintained registry `main` endpoint.

The registration preserves the latest published
`0.0.26-2cfc059c2cf1dc3b2f2b2ec1bcd70400b04ecb75`, the earlier
`0.0.26-51c838da6ff57295fde6e0bc3807841cb31a8568`, and every other published entry. It
retains the published cross-test visibility patch and four validation overlay
files. The BUILD overlay adds `registry_ci:gzip_tools`, which collects the
shared reproducible gzip executable while also analyzing its public toolchain
label. The version patch only adapts the fetched module identity. The source
contains the native-component implementation previously supplied by the
published registry patch; the complete carry-forward comparison is retained
with validation evidence.

The registration also retains the APT overlap-layer checks and explicit
Libtool outputs from published `0.0.25-3ee15ec9b4d99d7f8eae3e324cead79b203b451e`.

Common native coverage selects **50 build targets and 76 tests**. AMD64 adds
the two existing DocBook build targets and its runtime test, for **52 builds
and 77 tests**. ARM64 retains the common **50 builds and 76 tests**, matching
the source's explicit architecture support. The lists preserve native runtime
context, ORIGIN/RPATH, debug ownership, deployment timestamps, prefix mapping,
kernel tools and Bookworm Perl/Valgrind regressions. Shared patch/XML tools and
the locked Bookworm graph are covered explicitly. The gzip filegroup makes
deletion of either published gzip label fail analysis and retains a concrete
executable for artifact collection.

The dependency selections include `tar.bzl@0.10.5.sonic.2`,
`rules_python@1.9.0.sonic.1`, and `rules_distroless@0.9.4.sonic.17`; verify their
maintained-registry provenance with the final source and registry CI receipts.
Archive/recipe checks and complete version-comparison receipts are separate
from native build/test acceptance. Source CI does not replace the independent
registry-consumer matrix or a complete SONiC image build.
