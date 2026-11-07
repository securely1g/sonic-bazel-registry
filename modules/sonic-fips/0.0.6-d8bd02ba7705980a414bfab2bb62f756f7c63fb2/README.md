# FIPS cross-build and test support

This entry pins the single unpublished `0.0.6` candidate to commit
`d8bd02ba7705980a414bfab2bb62f756f7c63fb2`, an ordinary continuation of
[source release PR #20](https://github.com/securely1g/sonic-fips/pull/20)
and [Draft source PR #21](https://github.com/securely1g/sonic-fips/pull/21).
OpenSSH queries declared libedit pkg-config metadata through a private executable
launcher, matching upstream's quoted executable-path interface. The launcher
preserves declared prefix arguments and keeps metadata isolated from host paths.
Libedit and its real link probe, source OpenSSL, target loaders, other features
and all build outputs remain enabled. The earlier metadata revision failed on
both source-base architectures because a command string was used as a filename;
realistic quoted-call controls cover this correction. Exact native validation
remains pending. [Selected source](https://github.com/securely1g/sonic-fips/commit/d8bd02ba7705980a414bfab2bb62f756f7c63fb2).
This registry candidate remains Draft until its source prerequisite lands.

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
