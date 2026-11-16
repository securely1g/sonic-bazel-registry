# Native FRR/libFIB infrastructure dependency

Register maintained-master commit `c8e5486df0147c5652d015bb5ddd49b6dce6b655`, the merge of [infra #97](https://github.com/securely1g/sonic-build-infra/pull/97), for [buildimage #51](https://github.com/securely1g/sonic-buildimage/pull/51). It adds `fib_deps` and `fib_bookworm_deps` to the unified APT lock, preserving all 2,426 prior package records. Existing native tools, archive rules, target runtimes and installation RPATH support remain available.

The source archive is fetched from the maintained repository and verified by SHA-256. Its complete Git tree equals the reviewed contributor candidate. This replaces the unpublished contributor snapshot; published versions remain unchanged.
