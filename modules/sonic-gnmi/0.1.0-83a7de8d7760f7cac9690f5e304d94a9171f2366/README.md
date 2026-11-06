# Native AMD64 gNMI runtime and source TARs

Register public gNMI commit `83a7de8d7760f7cac9690f5e304d94a9171f2366` from [gNMI #2](https://github.com/securely1g/sonic-gnmi/pull/2), including [the subscription fixes](https://github.com/securely1g/sonic-gnmi/pull/1), for [buildimage #148](https://github.com/securely1g/sonic-buildimage/pull/148) and [issue #126](https://github.com/securely1g/sonic-buildimage/issues/126).

The owner builds the existing nine telemetry, dialout and gNMI/gNOI programs and exports runtime TARs, matching debug symbols, component sources and runtime metadata. SWSS Common owns the CGo binding; Management Common owns generated schemas and Go interfaces. No DEB producer is selected.

| Input | Before | After |
| --- | --- | --- |
| Management Common | Unlanded `1.0.1-24211db5...` copied into the review branch | Maintained `1.0.1-05f83dcab8fe2e1a0e0fc37ac172b289d6968e2b` from [#216](https://github.com/securely1g/sonic-bazel-registry/pull/216) |
| gNMI source | `6a854f16...` | `83a7de8d7760f7cac9690f5e304d94a9171f2366`, whose root and separate consumer select the landed owner |
| Shared Go types | Public goyang and ygot | The same published [goyang #212](https://github.com/securely1g/sonic-bazel-registry/pull/212) and [ygot #214](https://github.com/securely1g/sonic-bazel-registry/pull/214) entries |

The registered MODULE is the source MODULE with only its immutable version changed. The ordinary consumer retains SWSS Common `0.0.8-a0450924719a9f706125cc44a07dc88934935003`, infrastructure `0.0.25-3ee15ec9b4d99d7f8eae3e324cead79b203b451e`, `rules_go@0.64.1-sonic.1`, Go 1.25.9, its existing Go workspace and Distroless `.16`. It uses public owner mappings without source overrides or duplicate goyang/ygot patches.

All six build targets and three tests are unchanged: the separate consumer, runtime/debug/metadata/source TARs and generated YANG server, plus package/source contracts and installed telemetry against private Redis. Source CI separately owns the original suites, CodeQL and compiler canaries. The archive was verified against every source Git blob and mode; that check does not establish native acceptance. The source native dispatch was rejected by GitHub with HTTP 422: Actions disabled, despite enabled settings. Source native/CodeQL evidence is missing; registry native validation remains pending. Historical receipts retain their original source/catalog identities.

This initial registration targets native AMD64 Trixie. Keep Draft until gNMI #2 lands and current registry/consumer CI passes. ARM, ASAN and full VS installer acceptance are outside this registration.

<details>
<summary>Historical dependency review links</summary>

Earlier dependency iterations: [SWSS Common #199](https://github.com/securely1g/sonic-bazel-registry/pull/199), [infrastructure #218](https://github.com/securely1g/sonic-bazel-registry/pull/218), [Management Common #219](https://github.com/securely1g/sonic-bazel-registry/pull/219), [libnl #181](https://github.com/securely1g/sonic-bazel-registry/pull/181), and [Distroless #200](https://github.com/securely1g/sonic-bazel-registry/pull/200).

</details>
