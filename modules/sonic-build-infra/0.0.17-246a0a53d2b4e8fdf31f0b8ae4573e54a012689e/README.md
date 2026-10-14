# Repository sysroot and declared source-build tools

This candidate registers `sonic-build-infra` source `246a0a53d2b4e8fdf31f0b8ae4573e54a012689e`. It combines maintained `master` at `4429ada56a20a9d9cb01369271766991974472bb` with the required [repository sysroot #40](https://github.com/securely1g/sonic-build-infra/pull/40) and [Kerberos generators #41](https://github.com/securely1g/sonic-build-infra/pull/41). The source remains an unmerged integration snapshot.

The maintained foundation includes configure tools #36, compiler paths #37 and [SWIG feature definitions #44](https://github.com/securely1g/sonic-build-infra/pull/44). SWIG definitions let the source base in [image #30](https://github.com/securely1g/sonic-buildimage/pull/30), inherited by [image #13](https://github.com/securely1g/sonic-buildimage/pull/13), use the landed Common runtime while retaining its sysroot and Kerberos requirements.

`sonic-fips //symcrypt:core` uses `sysroots.debian` to expose pinned Trixie headers and libraries to LLVM. Its Kerberos source build uses declared `compile_et` and `mk_cmds` generators. Existing FIPS consumers can retain the earlier compatible immutable snapshot while this combined registration is reviewed.

The sole registry patch aligns the module version with its full source commit. Published versions and the separate configure-tools registration #60 are preserved. Native AMD64/ARM64 registry checks build the declared GNU tools and Kerberos generators, then test runtime availability, configure generation, compiler/library paths and Kerberos generation. Source #40 owns the separate LLVM sysroot checks; those are not represented as registry target coverage.
