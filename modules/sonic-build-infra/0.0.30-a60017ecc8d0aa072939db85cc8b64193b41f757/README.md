# Native FRR/libFIB infrastructure dependency

Register the reviewed source candidate from [infra #97](https://github.com/securely1g/sonic-build-infra/pull/97) for [buildimage #51](https://github.com/securely1g/sonic-buildimage/pull/51). It adds `fib_deps` and `fib_bookworm_deps` to the unified APT lock, preserving all 2,426 prior package records. Existing native tools, archive rules, target runtimes and installation RPATH support remain available.

This candidate pins the contributor source archive and SHA-256. After #97 lands, registration must select the actual maintained-master commit and its archive digest before Ready. Published versions remain unchanged.
