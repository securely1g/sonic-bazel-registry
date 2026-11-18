## Registry dependency refresh: `0.0.7-9abc81282153fd9844c24e4a8372a4240e7106a1`

Source: `securely1g/sonic-fips@9abc81282153fd9844c24e4a8372a4240e7106a1`, based on `1a8daf8dd8a3ad54de0e91a55b46fd5bbd206763`. Dependency targets are frozen to published registry snapshot `3d1cc5e8dfd553d2acbe4198e504a245e6bdbddf`. The source owns the module base version and dependency updates. The registry supplies the full commit-qualified identity and retains its existing integration behavior.

Full archive patch-application and build validation must be recorded separately.

# SONiC FIPS runtime and debug TARs

This version registers the merged OpenSSH libedit metadata fix from
[sonic-fips #21](https://github.com/securely1g/sonic-fips/pull/21).
The OpenSSH configure step queries the declared libedit pkg-config metadata
while keeping the source-built OpenSSL 3.5.7 headers ahead of the SDK's generic
include directory. Libedit's own include and library flags remain available
to the feature and link probes.

The source archive is pinned to
[18a778db](https://github.com/securely1g/sonic-fips/commit/18a778db501d455f8a1b6d1e3ef8e17121661177).
The registry patch appends this commit to the upstream module version. The
registered build and test targets are listed in [presubmit.json](presubmit.json).
Both native AMD64 and ARM64 consumers build the OpenSSL, OpenSSH, Kerberos and
SymCrypt outputs and run the package, timestamp and OpenSSL integration tests.

## ARM64 cross-validation

The registry presubmit retains all 18 build targets and six package tests.
On AMD64-to-ARM64 runs, Kerberos measures its three configure answers with
the selected target compiler and ARM runtime. All original OpenSSL recipes
use target Perl. Only `30-test_afalg.t` invokes the worker's ARM64 kernel
executor for Linux native asynchronous I/O. The guest's development packages
supply zlib and Zstandard for the original static SDK consumer.

This route uses the worker's corrected userspace executor, ARM compression
development packages and explicit kernel executor. See
[worker #92](https://github.com/securely1g/agi-projects/pull/92),
[worker #93](https://github.com/securely1g/agi-projects/pull/93) and
[worker #94](https://github.com/securely1g/agi-projects/pull/94).
