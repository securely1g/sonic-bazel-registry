# FIPS metadata generated from Debian recipes

Registers [sonic-fips #7](https://github.com/securely1g/sonic-fips/pull/7),
source `5d1dfc86d733046fe22fa3cb699db639314af49f`. The public
`@sonic-fips//:runtime_packages.json` is generated from the four existing Debian
recipes and nine native runtime TARs. No handwritten package metadata remains
in this source revision. The published `0.0.2-df34b541eb08d1a6a4b039e69c4d716c84566061`
entry and its inputs remain unchanged.

For example, OpenSSL's prepared changelog supplies `3.5.7-1~deb13u2`; its existing
SONiC preparation policy adds `+fips`. Metadata generation produces
`Version: 3.5.7-1~deb13u2+fips` without a second version literal, and preserves
Debian's generated `perl:any` dependency on the `openssl` package. SymCrypt
reuses its existing finalized binary control and derives `libc6 (>= 2.14)` and
`libssl3t64 (>= 3.4.0)` from the actual AMD64 ELF output, in addition to the
recipe's explicit `openssl (>= 3.0)`. These fields were observed in the native
AMD64 producer build; registry CI independently rebuilds both architectures.

[Buildimage #30](https://github.com/securely1g/sonic-buildimage/pull/30) and
[#13](https://github.com/securely1g/sonic-buildimage/pull/13) use the generated
controls with source TARs for the FIPS-enabled base and Syncd images. The rule
comes from [infra #58](https://github.com/securely1g/sonic-build-infra/pull/58)
through [registry #120](https://github.com/securely1g/sonic-bazel-registry/pull/120),
which retains the static C tool-launcher fix and [cache-safe execution tools](https://github.com/securely1g/sonic-build-infra/pull/64).

The entry retains all runtime/debug build targets, package checks and the
OpenSSL/SymCrypt integration test on native AMD64 and ARM64. Metadata generation
creates no DEB and runs no maintainer scripts. Registry CI retains the generated
JSON alongside the source runtime/debug TARs.
