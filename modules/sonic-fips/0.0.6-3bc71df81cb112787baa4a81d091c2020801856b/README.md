# FIPS cross-build and test support

This entry pins the cumulative `0.0.6` source to commit
`3bc71df81cb112787baa4a81d091c2020801856b`. The registry patch adds the
commit suffix to the declared version. The source combines the declared
Kerberos/OpenSSH loader, target SymCrypt tools and the OpenSSL TAP interpreter
selection. [Cumulative source](https://github.com/securely1g/sonic-fips/commit/3bc71df81cb112787baa4a81d091c2020801856b)

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
