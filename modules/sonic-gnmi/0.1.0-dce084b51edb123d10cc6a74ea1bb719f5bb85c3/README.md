# Register merged sonic-gnmi sources

Source: [securely1g/sonic-gnmi@dce084b5](https://github.com/securely1g/sonic-gnmi/commit/dce084b51edb123d10cc6a74ea1bb719f5bb85c3).

This entry uses the latest maintained-branch commit captured on 2026-11-18. It preserves the owner module base `0.1.0` and its dependency declarations. The registry qualifies the version with the full source commit and retains existing compatible consumer tests and registry adaptations.

The following declaration updates remain deferred because they have not landed in this source owner:

| Dependency | Merged owner selection | Deferred refresh selection |
|---|---|---|
| sonic-build-infra | `0.0.37-316e298e77ab5cfa69af9b0c05ec24d5d94bbe1e` | `0.0.38-0baa4acc9eac9ccc793b81104b1580d530271cbe` |
| libnl3 | `3.7.0.sonic.7` | `3.7.0.sonic.8` |
| rules_distroless | `0.9.4.sonic.20` | `0.9.4.sonic.22` |
| libyang | `3.12.2.sonic.6` | `3.12.2.sonic.8` |

Archive integrity, complete patch application, overlay checksums and module identity were checked locally. This preparation does not claim a completed Bazel build or passing CI.
