# Register merged sonic-yang-models sources

Source: [securely1g/sonic-buildimage@dd732f95](https://github.com/securely1g/sonic-buildimage/commit/dd732f9512a84966487951250adae8e3e5c9943e).

This entry uses the latest maintained-branch commit captured on 2026-11-18. It preserves the owner module base `1.0.1` and its dependency declarations. The registry qualifies the version with the full source commit and retains existing compatible consumer tests and registry adaptations.

The following declaration updates remain deferred because they have not landed in this source owner:

| Dependency | Merged owner selection | Deferred refresh selection |
|---|---|---|
| rules_python | `1.8.0` | `1.9.0.sonic.1` |
| sonic-build-infra | `0.0.37-d31541a95fdf477302f1b109f2105eee81c86617` | `0.0.38-0baa4acc9eac9ccc793b81104b1580d530271cbe` |

Archive integrity, complete patch application, overlay checksums and module identity were checked locally. This preparation does not claim a completed Bazel build or passing CI.
