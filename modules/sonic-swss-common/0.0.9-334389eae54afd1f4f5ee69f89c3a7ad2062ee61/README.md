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
