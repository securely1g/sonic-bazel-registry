# Native AMD64 gNMI runtime and source TARs

Register public gNMI commit `3cc2cba22ba980128518aafe4ddae14aeebebb08` from [gNMI #2](https://github.com/securely1g/sonic-gnmi/pull/2), including [the subscription fixes](https://github.com/securely1g/sonic-gnmi/pull/1), for [buildimage #148](https://github.com/securely1g/sonic-buildimage/pull/148) and [issue #126](https://github.com/securely1g/sonic-buildimage/issues/126).

The owner builds the existing nine telemetry, dialout and gNMI/gNOI programs and exports runtime TARs, matching debug symbols, component sources and runtime metadata. SWSS Common owns the CGo binding; Management Common owns generated schemas and Go interfaces. No DEB producer is selected.

| Input | Before | After |
| --- | --- | --- |
| Management Common | Unlanded review candidates copied into the review branch | Maintained `1.0.1-05f83dcab8fe2e1a0e0fc37ac172b289d6968e2b` from [#216](https://github.com/securely1g/sonic-bazel-registry/pull/216) |
| gNMI source | Unlanded review candidates | `3cc2cba22ba980128518aafe4ddae14aeebebb08`, whose root and separate consumer select the landed owner |
| Shared Go types | Public goyang and ygot | The same published [goyang #212](https://github.com/securely1g/sonic-bazel-registry/pull/212) and [ygot #214](https://github.com/securely1g/sonic-bazel-registry/pull/214) entries |

The registered MODULE is the source MODULE with only its immutable version changed. The consumer preserves SWSS Common `0.0.9-334389eae54afd1f4f5ee69f89c3a7ad2062ee61`, Management Common `1.0.1-05f83dcab8fe2e1a0e0fc37ac172b289d6968e2b`, infrastructure `0.0.26-51c838da6ff57295fde6e0bc3807841cb31a8568`, `rules_go@0.64.1-sonic.1`, Go 1.25.9, its existing Go workspace and Distroless `.16`. It uses public owner mappings without source overrides or duplicate goyang/ygot patches.

All six build targets and three tests are unchanged: the separate consumer, runtime/debug/metadata/source TARs and generated YANG server, plus package/source contracts and installed telemetry against private Redis. Source CI passed all original suites, Bazel gNMI (32 test targets), CodeQL, and subscription race tests on gNMI #2 at `82e6096` before landing on `master` at `3cc2cba22ba980128518aafe4ddae14aeebebb08`. The archive was verified against every source Git blob and mode. Historical receipts retain their original source/catalog identities.

This initial registration targets native AMD64 Trixie. ARM, ASAN and full VS installer acceptance are outside this registration.

<details>
<summary>Historical dependency review links</summary>

Earlier dependency iterations: [SWSS Common #199](https://github.com/securely1g/sonic-bazel-registry/pull/199), [infrastructure #218](https://github.com/securely1g/sonic-bazel-registry/pull/218), [Management Common #219](https://github.com/securely1g/sonic-bazel-registry/pull/219), [libnl #181](https://github.com/securely1g/sonic-bazel-registry/pull/181), and [Distroless #200](https://github.com/securely1g/sonic-bazel-registry/pull/200).

</details>
