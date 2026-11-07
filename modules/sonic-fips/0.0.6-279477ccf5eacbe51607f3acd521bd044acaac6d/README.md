# FIPS cross-build and test support

This entry pins the `0.0.6` diagnostic candidate to commit
`279477ccf5eacbe51607f3acd521bd044acaac6d`, an ordinary child of merged
[source release PR #20](https://github.com/securely1g/sonic-fips/pull/20).
The source adds a bounded excerpt of the failed OpenSSH libedit link check
while preserving configure's original failure status, `--with-libedit`,
source OpenSSL, declared target loaders and all build outputs.
It diagnoses the observed Framework failure; it does not claim to fix it.
[Selected source](https://github.com/securely1g/sonic-fips/commit/279477ccf5eacbe51607f3acd521bd044acaac6d).
The diagnostic source remains in [Draft PR #21](https://github.com/securely1g/sonic-fips/pull/21); this registry candidate remains Draft until that prerequisite lands.

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
