## Registry dependency refresh: `0.0.10-a3bc237524f643c0fa4bd404762e17128d6e5f10`

Source: `securely1g/sonic-swss-common@a3bc237524f643c0fa4bd404762e17128d6e5f10`, based on `ba4b42f08ce2aef7926c6dc39ed91e391853384f`. Dependency targets are frozen to published registry snapshot `3d1cc5e8dfd553d2acbe4198e504a245e6bdbddf`. The source owns the module base version and dependency updates. The registry supplies the full commit-qualified identity and retains its existing integration behavior.

Full archive patch-application and build validation must be recorded separately.

The old `0002-libyang-runtime-libraries.patch` is omitted because the source already contains its exact libpcre2/libxxhash runtime block, and the source now selects libyang `3.12.2.sonic.8`. Existing runtime regression targets are retained.

# Common native, Go, Rust and testing interfaces

This registration selects landed master source
`334389eae54afd1f4f5ee69f89c3a7ad2062ee61` from [Common #42](https://github.com/securely1g/sonic-swss-common/pull/42).
It retains the Go import interface from [Common #38](https://github.com/securely1g/sonic-swss-common/pull/38),
the shared libnl providers from [Common #41](https://github.com/securely1g/sonic-swss-common/pull/41),
and the async Rust library and testing helpers from [Common #42](https://github.com/securely1g/sonic-swss-common/pull/42).
The source also includes the landed native loader, ZMQ, Lua-directory and root-owned runtime TAR changes.
Published Common entries, including `.8-a0450924`, are preserved unchanged.

DASH HA's `swbus-actor` and `swss-common-bridge` enable Common's Cargo `async`
feature. They consume `//crates/swss-common:swss_common_async` and
`//crates/swss-common-testing:swss_common_testing_async` from this owner.
Default consumers retain `:swss_common` and `:swss_common_testing`.
These variants share their public Rust types and the existing
`sonic-rust-deps` dependencies. gNMI consumes the same owner's Go bindings;
Common and Linkmgrd consume the same native libnl providers.

The ordinary external consumer retains all 16 output targets and 24 tests.
They include C++, Go, CLI, Python, Rust, detached debug, archive ownership,
shared Serde and async Tokio checks.

| Input or action | Previous registration | Current registration |
| --- | --- | --- |
| HA async/testing and gNMI Go interfaces | Landed master from PRs #38, #41 and #42 | Cumulative master `334389e` supplies both interfaces and preserves all tests |
| Common's infrastructure dependency | Landed master selects `sonic-build-infra` `0.0.26-51c838da` | Module, version patch and ordinary consumer agree on published `0.0.26-51c838da` |
| Distroless and libyang | Distroless .15, libyang .4 | Both select published distroless .16 and libyang .6 |

The Common-owned test runtime includes libyang's pinned PCRE2 and xxhash
runtime payloads when YANG is enabled, backported from [Common #45](https://github.com/securely1g/sonic-swss-common/pull/45).
