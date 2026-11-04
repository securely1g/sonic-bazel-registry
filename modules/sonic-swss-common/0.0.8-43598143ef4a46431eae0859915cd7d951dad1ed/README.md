# Common native, Go, Rust and testing interfaces

This registration selects cumulative source
`43598143ef4a46431eae0859915cd7d951dad1ed`. It retains the Go import interface
from [Common #38](https://github.com/securely1g/sonic-swss-common/pull/38),
the shared libnl providers from [Common #41](https://github.com/securely1g/sonic-swss-common/pull/41),
and the async Rust library and testing helpers from
[Common #42](https://github.com/securely1g/sonic-swss-common/pull/42).
Those source changes remain independent reviews. The source also includes the
landed native loader, ZMQ, Lua-directory and root-owned runtime TAR changes.
Published Common entries, including `.8-a0450924`, are preserved unchanged.

DASH HA's `swbus-actor` and `swss-common-bridge` enable Common's Cargo `async`
feature. They consume `//crates/swss-common:swss_common_async` and
`//crates/swss-common-testing:swss_common_testing_async` from this owner.
Default consumers retain `:swss_common` and `:swss_common_testing`.
These variants share their public Rust types and the existing
`sonic-rust-deps` dependencies. gNMI consumes the same owner's Go bindings;
Common and Linkmgrd consume the same native libnl providers.

The ordinary external consumer retains all 16 output targets and 24 tests from
the preceding registration. They include C++, Go, CLI, Python, Rust, detached
debug, archive ownership, shared Serde and async Tokio checks. The complete
13-output/19-test contract from [registry #167](https://github.com/securely1g/sonic-bazel-registry/pull/167)
is a subset of this contract. The AMD64/ARM64 matrix is preserved; current
Docker validation is AMD64 and does not establish ARM64 or image acceptance.
No DEB-producing targets are selected.

| Input or action | Previous registration | Current registration |
| --- | --- | --- |
| HA async/testing and gNMI Go interfaces | Separate draft registrations selected different Common sources | One cumulative source supplies both interfaces and preserves every existing test |
| Common's infrastructure dependency | The older draft `2cfc059c` could be selected by its standalone module | Module, version patch and ordinary consumer select `3ee15ec9` from [registry #218](https://github.com/securely1g/sonic-bazel-registry/pull/218) |
| Distroless dependency | The source minimum was `.13` and the ordinary consumer pinned `.15` | Both select published `.16` |

The sole source patch sets the registry module version and these dependency
selections; it changes no producer, header, runtime or test source. Source
archive integrity is unchanged. Source-owned public targets and installed
runtime metadata remain the consumer boundary.

This is the proposed coordinated refresh of
[registry #199](https://github.com/securely1g/sonic-bazel-registry/pull/199).
The older #167 registration must be superseded only after its source features,
coverage and consumers are verified against this candidate. Closed
[registry #201](https://github.com/securely1g/sonic-bazel-registry/pull/201)
remains historical evidence, not a current dependency or a new acceptance
claim. The independent source #38/#41/#42 reviews remain required.

Keep this registration Draft while those sources or the infrastructure
prerequisite are unlanded. Fresh configured and ordinary-consumer acceptance
on these current registration inputs is pending; earlier successful image and
source receipts retain their original source/catalog identities.

This dependency refresh selects maintained infrastructure source 3ee15ec9 through
registry #218. Its numeric version is .25; published .26 entries remain intact.
Fresh module-graph checks must verify the selected version, followed by the
unchanged ordinary-consumer outputs and tests. This metadata/source-patch proof
does not establish native or image acceptance. Existing worker runs and earlier
receipts retain their exact preceding dependency inputs.
