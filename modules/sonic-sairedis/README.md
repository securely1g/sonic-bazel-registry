# sonic-sairedis

The current registration is `0.0.0-d81b2a91ab8ab89b4391ad5c9a93d033cd061942`, from [source PR #1](https://github.com/securely1g/sonic-sairedis/pull/1).

It fixes external consumer test launchers while preserving the public C++ interfaces. Native AMD64/ARM64 validation builds the shared libraries and executes the dynamic consumer with the protobuf header fix from [Distroless #28](https://github.com/securely1g/sonic-bazel-registry/pull/28).

Only the current draft registration is included. Previous immutable registrations remain available at [the retained snapshot](https://github.com/securely1g/sonic-bazel-registry/tree/archive/pr20-before-native-distroless-20261002) for consumers that still pin them.
