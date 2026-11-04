# Native AMD64 gNMI runtime and source TARs

Register the unchanged gNMI source `ce49e93eb3a0cff8daf77a3092535d76265ebc3d` from [gNMI #2](https://github.com/securely1g/sonic-gnmi/pull/2), which includes [#1](https://github.com/securely1g/sonic-gnmi/pull/1), for [buildimage #148](https://github.com/securely1g/sonic-buildimage/pull/148) and [issue #126](https://github.com/securely1g/sonic-buildimage/issues/126).

The owner builds the existing nine telemetry, dialout and gNMI/gNOI programs and exports runtime, matching debug symbols, component sources and runtime metadata. SWSS Common owns the reusable CGo binding; Management Common owns generated schemas and Go interfaces. Legacy Make remains available. No DEB producer is selected.

The registry and separate consumer select the same current shared dependencies:

| Dependency | Selected input | Registration |
| --- | --- | --- |
| SWSS Common | `0.0.8-43598143ef4a46431eae0859915cd7d951dad1ed` | [#199](https://github.com/securely1g/sonic-bazel-registry/pull/199) |
| Build infrastructure | `0.0.25-3ee15ec9b4d99d7f8eae3e324cead79b203b451e` | [#218](https://github.com/securely1g/sonic-bazel-registry/pull/218) |
| Management Common | `1.0.0-71eb5f710b5347ca0510ee8e3f5294a7c64bb744` | [#219](https://github.com/securely1g/sonic-bazel-registry/pull/219), child of [#216](https://github.com/securely1g/sonic-bazel-registry/pull/216) |
| Shared goyang / ygot | `0.0.0.sonic.1-20200309174518-a00bece872fc` / `0.7.1.sonic.1` | published [#212](https://github.com/securely1g/sonic-bazel-registry/pull/212) / [#214](https://github.com/securely1g/sonic-bazel-registry/pull/214) |
| libnl / Distroless | published `3.7.0.sonic.7` / `0.9.4.sonic.16` | [#181](https://github.com/securely1g/sonic-bazel-registry/pull/181) / [#200](https://github.com/securely1g/sonic-bazel-registry/pull/200) |

The existing MODULE patch aligns the fetched source with these registry declarations byte-for-byte. The ordinary consumer uses public owner mappings without module/source overrides or duplicated goyang/ygot patches. The source archive integrity stays unchanged. Its Go workspace also receives the existing shared-root compatibility patch, selecting `golang.org/x/text v0.39.0` and `golang.org/x/sync v0.21.0`; both replacements match the composed consumer graph and retain Go 1.25.9. The `rules_go@0.64.1-sonic.1` declaration, unrelated feature patches, optimized configuration and empty global Go tags are unchanged.

All six build targets and three tests are preserved. They build a separate public-library consumer plus runtime/debug/source artifacts and the generated YANG server; checks inspect package/source contracts and exercise telemetry/gnmi_get against private Redis fixtures. Source CI separately owns the original suites, CodeQL and compiler canaries. Fresh ordinary-consumer and downstream image acceptance is required for this updated dependency graph. Historical receipts remain associated with their original source/catalog revisions.

This initial registration is scoped to native AMD64 Trixie; ARM, ASAN and full VS installer acceptance remain outside it. Keep Draft until the required source and registry changes land, the registration targets maintained main, and its current CI passes.

This dependency refresh selects maintained infrastructure source 3ee15ec9 through
registry #218. Its numeric version is .25; published .26 entries remain intact.
Fresh module-graph checks must verify the selected version, followed by the
unchanged ordinary-consumer outputs and tests. This metadata/source-patch proof
does not establish native or image acceptance. Existing worker runs and earlier
receipts retain their exact preceding dependency inputs.
