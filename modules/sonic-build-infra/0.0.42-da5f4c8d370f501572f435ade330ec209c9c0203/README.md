# Target-aware static archive stripping

This registration publishes [merged sonic-build-infra 0baa4acc9eac9ccc793b81104b1580d530271cbe](https://github.com/securely1g/sonic-build-infra/commit/0baa4acc9eac9ccc793b81104b1580d530271cbe) with the target-aware strip_static_archive rule and its behavior tests.

It inherits every overlay and presubmit target from `0.0.37-316e298e77ab5cfa69af9b0c05ec24d5d94bbe1e`, including the existing APT collections and kernel tool checks. It adds two native archive tests and the archive checker build. AMD64-to-ARM64 archive checking is also covered by the source repository CI.
