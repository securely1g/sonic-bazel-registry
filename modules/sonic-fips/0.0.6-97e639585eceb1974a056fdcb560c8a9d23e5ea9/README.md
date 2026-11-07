# FIPS cross-build and test support

This entry pins the single unpublished `0.0.6` candidate to commit
`97e639585eceb1974a056fdcb560c8a9d23e5ea9`, an ordinary continuation of
[source release PR #20](https://github.com/securely1g/sonic-fips/pull/20)
and [Draft source PR #21](https://github.com/securely1g/sonic-fips/pull/21).
OpenSSH now queries the declared libedit pkg-config metadata instead of
falling back to the guessed `-lcurses` link input. The package metadata
closure is isolated from host paths, following the existing Kerberos
adapter. Libedit and its real link probe, source OpenSSL, target loaders,
other features and all build outputs remain enabled. The bounded link
failure diagnostic remains available; exact native validation is pending.
[Selected source](https://github.com/securely1g/sonic-fips/commit/97e639585eceb1974a056fdcb560c8a9d23e5ea9).
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
