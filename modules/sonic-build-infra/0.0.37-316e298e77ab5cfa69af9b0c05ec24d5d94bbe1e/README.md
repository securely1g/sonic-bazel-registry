# Shared Trixie APT collections for OTEL, P4RT and DASH Engine

This registration publishes the build-infra revision that merged the [P4RT
and DASH Engine selections](https://github.com/securely1g/sonic-build-infra/pull/106)
and the [OTEL runtime selection](https://github.com/securely1g/sonic-build-infra/pull/105).
It preserves the earlier DASH HA and MACsec collections.

| Image | AMD64 package collections |
| --- | --- |
| OTEL | `otel_debian` |
| P4RT | `p4rt_debian`, `p4rt_debug_debian`, `p4rt_test_debian` |
| DASH Engine | `dash_engine_debian`, `dash_engine_debug_debian` |

The [source archive](https://github.com/securely1g/sonic-build-infra/commit/316e298e77ab5cfa69af9b0c05ec24d5d94bbe1e) contains
79 collections and 2,454 package records. The registration retains the existing
cross-test visibility patch, CI overlays and native presubmit targets.
