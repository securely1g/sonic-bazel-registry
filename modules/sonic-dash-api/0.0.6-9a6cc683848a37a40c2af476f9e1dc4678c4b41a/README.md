## Registry dependency refresh: `0.0.6-9a6cc683848a37a40c2af476f9e1dc4678c4b41a`

Source: `securely1g/sonic-dash-api@9a6cc683848a37a40c2af476f9e1dc4678c4b41a`, based on `1b371241ff886c240352d270de11ff2abca048c8`. Dependency targets are frozen to published registry snapshot `3d1cc5e8dfd553d2acbe4198e504a245e6bdbddf`. The source owns the module base version and dependency updates. The registry supplies the full commit-qualified identity and retains its existing integration behavior.

Full archive patch-application and build validation must be recorded separately.

# sonic-dash-api `0.0.5` from landed master

Registers landed source commit `9b2893e890734a2db0c53a5e5c64b031ec0dcfbd`,
which is `sonic-dash-api` `master` after
[API #8](https://github.com/securely1g/sonic-dash-api/pull/8). It carries:

| API PR | Change |
| --- | --- |
| [#5](https://github.com/securely1g/sonic-dash-api/pull/5) | Native DASH API builds use the published build tools |
| [#7](https://github.com/securely1g/sonic-dash-api/pull/7) | The original DASH HA protobuf schema (`ha_schema_sources`, `bazel:ha_schema_descriptor`) is exposed separately from the current API schema |
| [#8](https://github.com/securely1g/sonic-dash-api/pull/8) | Runtime package metadata (`runtime_packages.json`) is exported for OCI consumers |

The actual HA source uses API schema `18a29c1c`, where `HaScopeConfigKey` has
`ha_scope_id=1` and `vdpu_id=2`. Current API consumers use the later, reversed
numbers. The owner exposes the three original files separately, so the current
C++ and Python targets keep their schema. The real protoc descriptor/hash test
(`bazel:ha_schema_test`) protects this wire contract.

The source MODULE already pins published `sonic-build-infra`
`0.0.25-34de7330…` and Distroless `0.9.4.sonic.15`. The native consumer selects
the same published versions, so this entry depends on no unpublished registry
candidate. No DEBs are built.

This entry supersedes the unpublished `0.0.5-6adc606f…` (closed #140),
`0.0.5-edc5cc5d…` (closed #156) and `0.0.5-fd8eab1b…` proposals.
