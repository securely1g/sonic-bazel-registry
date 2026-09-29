# sonic-sairedis

The current registration is `0.0.0-d81b2a91ab8ab89b4391ad5c9a93d033cd061942`, from [source PR #1](https://github.com/securely1g/sonic-sairedis/pull/1).

The previous `0.0.0-df4319696743f4804053ab68c5af1a2b8254dcb4` entry remains available with its original contents. It is marked yanked because its external test launcher changes to the main repository working directory and fails before running the consumer. The replacement fixes only that launcher; public C++ interfaces and production sources are unchanged. Consumers requiring the historical input can retain their immutable registry snapshot.

Registry [CI #21](https://github.com/securely1g/sonic-bazel-registry/pull/21) validates the yanked entry metadata and inputs before excluding its known-broken execution job. The replacement retains the native AMD64/ARM64 build and uncached dynamic consumer checks.
