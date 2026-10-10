# Declare APT selection policy inputs

This source adds an optional `policy` JSON input to `apt_layer`. Selectors can
receive policy alone, a retained package manifest alone, or both. Both files are
declared action inputs, so changes invalidate selection. Existing positional and
keyword callers keep working; calls with neither input fail during analysis.

Buildimage Orchagent [PR #15](https://github.com/securely1g/sonic-buildimage/pull/15)
and Syncd-vs [PR #13](https://github.com/securely1g/sonic-buildimage/pull/13) use this
API for BUILD-declared policies and one shared selector. This entry selects
`8043a299756436464a8b58662921dfd50172a3ff`, the maintained-master merge of
[Infrastructure #29](https://github.com/securely1g/sonic-build-infra/pull/29),
and excludes inherited-package replacements.
Syncd selects FIPS OpenSSH in runtime; debug inherits it unchanged.

Native AMD64/ARM64 presubmit tests legacy manifest selection, policy-only and
policy-plus-manifest assembly, dependency checks and Protobuf headers. Fixtures
import existing package archives and produce TARs; they do not build DEBs.
