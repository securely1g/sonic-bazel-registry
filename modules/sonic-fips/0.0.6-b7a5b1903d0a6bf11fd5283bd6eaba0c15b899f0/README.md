# FIPS cross-build and test support

This entry pins the single unpublished `0.0.6` candidate to commit
`b7a5b1903d0a6bf11fd5283bd6eaba0c15b899f0`, an ordinary continuation of
[source release PR #20](https://github.com/securely1g/sonic-fips/pull/20)
and [source PR #21](https://github.com/securely1g/sonic-fips/pull/21).
OpenSSH queries its declared libedit metadata through an executable pkgconf
launcher. The launcher filters the redundant generic shared SDK include root,
retains `/editline` and all library flags, and isolates inherited pkgconf settings.
This prevents the imported SDK headers from outranking source OpenSSL; the strict
header/library check, source OpenSSL 3.5.7, libedit feature/link probes and target
loader order remain unchanged. The observed Framework failure passed libedit
and rejected headers 3.5.6 paired with library 3.5.7. Nine guarded methods across
19 shell/metadata fixtures passed; current source CI and exact Framework native
acceptance remain pending. [Selected source](https://github.com/securely1g/sonic-fips/commit/b7a5b1903d0a6bf11fd5283bd6eaba0c15b899f0).
This registry candidate remains Draft until its source prerequisite lands and
its temporary CI coverage gap is resolved.

The registry patch only adds the commit suffix to the declared version.
The cumulative source retains the Kerberos/OpenSSH target loader, SymCrypt
tools and OpenSSL TAP interpreter selection from the merged release.

The presubmit retains the prior 18 build targets and six package tests.
On AMD64-to-ARM64 runs, Kerberos measures its three configure answers with
the selected target compiler and ARM runtime. All original OpenSSL recipes
use target Perl. Only `30-test_afalg.t` invokes the worker's ARM64 kernel
executor for Linux native asynchronous I/O. The guest's development packages
supply zlib and Zstandard for the original static SDK consumer.

The ARM64 cross route for this version requires the worker image built
with the corrected userspace executor, ARM compression development packages
and explicit kernel executor. [Worker #92](https://github.com/securely1g/agi-projects/pull/92),
[worker #93](https://github.com/securely1g/agi-projects/pull/93) and
[worker #94](https://github.com/securely1g/agi-projects/pull/94).
