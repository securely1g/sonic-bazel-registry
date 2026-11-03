# Common native, Rust and testing interfaces

This sole unreleased Common candidate selects source `43598143ef4a46431eae0859915cd7d951dad1ed`.
It preserves the native loader, Go binding, ZMQ, Lua-directory and shared libnl
interfaces from Common PRs #37–#41, and adds [Common #42](https://github.com/securely1g/sonic-swss-common/pull/42)'s
source-owned async Rust library and matching test helpers.

DASH HA's `swbus-actor` and `swss-common-bridge` enable Common's Cargo `async`
feature. They can now consume `//crates/swss-common:swss_common_async` and
`//crates/swss-common-testing:swss_common_testing_async` from the owner, without
compiling another copy of Common. Default consumers retain `:swss_common` and
use `//crates/swss-common-testing:swss_common_testing` when needed. Matching
variants preserve public Rust type identity. All third-party Rust dependencies
come from the existing shared `sonic-rust-deps` module.

The ordinary external consumer retains every previous target and test, adding
three library targets and three tests: 16 build targets and 24 tests in total.
The new tests cover Common's existing unit behavior with async enabled, the
public testing-helper types, shared Serde traits and the async adapter running
on shared Tokio. They do not require an ambient Redis server. The existing
AMD64/ARM64 registry matrix is retained; the current Docker migration scope is
AMD64. Source CI also runs both YANG modes.

Existing C++/Go/CLI/runtime and detached-debug tests remain in the contract.
Common and Linkmgrd use the same native libnl providers, while each owner keeps
its runtime TAR. gNMI retains its import spelling and declared Lua runtime.
This registration is not a claim that the HA or gNMI container is complete.
The HA source and image tasks are [buildimage #104](https://github.com/securely1g/sonic-buildimage/issues/104)
and [#128](https://github.com/securely1g/sonic-buildimage/issues/128).

The only source patch sets the registry module version. Published Common
versions are unchanged, and the preceding .8 candidate is replaced in this
stack. No DEB-producing targets are selected.

Keep the registration Draft until the required source and registry contents
land. Its review base retains [registry #180](https://github.com/securely1g/sonic-bazel-registry/pull/180)'s
Common features and [#181](https://github.com/securely1g/sonic-bazel-registry/pull/181)'s
native libnl .7, with the current infrastructure candidate from
[#195](https://github.com/securely1g/sonic-bazel-registry/pull/195).
The external consumer selects that same infrastructure candidate and published
`sonic-rust-deps` .4 explicitly; its generated root overrides prevent the older
unpublished infrastructure declaration in libnl from selecting a removed entry.

The ordinary consumer selects published Distroless `.15`, matching the image
graph. The preceding `.13` override predates the published native ZMQ exports
and would force a version below libnl .7's `.14` requirement.

## Runtime TAR ownership

[Common #43](https://github.com/securely1g/sonic-swss-common/pull/43) makes the
CLI and Python runtime archives explicitly root-owned. The extended existing
archive check covers those payloads and rejects builder-dependent UID/GID
headers. It preserves installed bytes, modes, timestamps and debug pairing.

This review source combines Common #42 with the exact independent #43 feature
commit; the async/testing and archive-ownership changes remain separate review
units. All 16 existing output targets and 24 tests are retained unchanged. The
sole unpublished .8 candidate is replaced; no published entry is modified.

The registration module and source MODULE patch now select infrastructure `0.0.26-2cfc059c2cf1dc3b2f2b2ec1bcd70400b04ecb75` from [registry #209](https://github.com/securely1g/sonic-bazel-registry/pull/209), together with the aligned libnl [#181](https://github.com/securely1g/sonic-bazel-registry/pull/181). This replaces a removed unpublished minimum and lets ordinary downstream consumers resolve the current catalog. The source archive, ownership fix and complete 16-output/24-test presubmit are preserved; fresh dependency-graph acceptance is pending.
