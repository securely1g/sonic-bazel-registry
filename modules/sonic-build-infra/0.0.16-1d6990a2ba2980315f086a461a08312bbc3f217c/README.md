# Shared sysroot and declared source-build tools

This candidate registers maintained `sonic-build-infra` commit `1d6990a2ba2980315f086a461a08312bbc3f217c`, after [shared sysroot #40](https://github.com/securely1g/sonic-build-infra/pull/40) and [Kerberos generators #41](https://github.com/securely1g/sonic-build-infra/pull/41) landed. The version uses the source module's `0.0.16` base version and full landed commit.

Both GCC and LLVM use the same combined AMD64/ARM64 sysroot. The source includes the declared configure tools, Kerberos generators, SWIG definitions and landed Rust fixes. Source-built images and FIPS consumers need this shared support; their earlier immutable integration snapshots remain available while their own dependency migrations are validated.

The sole registry patch aligns the module version with its full source commit. Published versions and the separate configure-tools registration are preserved. Native AMD64/ARM64 registry checks build the GNU tools and Kerberos generators, then test runtime availability, configure generation, compiler/library paths and Kerberos generation. Source #40 supplies the separate four compiler/architecture sysroot checks; registry checks do not substitute for that coverage.
