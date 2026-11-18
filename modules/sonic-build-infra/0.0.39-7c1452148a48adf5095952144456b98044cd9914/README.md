## Registry dependency refresh: `0.0.39-7c1452148a48adf5095952144456b98044cd9914`

Source: `securely1g/sonic-build-infra@7c1452148a48adf5095952144456b98044cd9914`, based on `0baa4acc9eac9ccc793b81104b1580d530271cbe`. Dependency targets are frozen to published registry snapshot `3d1cc5e8dfd553d2acbe4198e504a245e6bdbddf`. The source owns the module base version and dependency updates. The registry supplies the full commit-qualified identity and retains its existing integration behavior.

Full archive patch-application and build validation must be recorded separately.

# Target-aware static archive stripping

This registration publishes [merged sonic-build-infra 0baa4acc9eac9ccc793b81104b1580d530271cbe](https://github.com/securely1g/sonic-build-infra/commit/0baa4acc9eac9ccc793b81104b1580d530271cbe) with the target-aware strip_static_archive rule and its behavior tests.

It inherits every overlay and presubmit target from `0.0.37-316e298e77ab5cfa69af9b0c05ec24d5d94bbe1e`, including the existing APT collections and kernel tool checks. It adds two native archive tests and the archive checker build. AMD64-to-ARM64 archive checking is also covered by the source repository CI.
