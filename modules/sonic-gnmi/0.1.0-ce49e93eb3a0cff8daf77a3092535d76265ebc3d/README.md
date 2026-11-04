# Native AMD64 gNMI runtime and source TARs

Register [gNMI #2](https://github.com/securely1g/sonic-gnmi/pull/2)'s native source producer for [buildimage #148](https://github.com/securely1g/sonic-buildimage/pull/148), which addresses the `docker-sonic-gnmi` migration in [issue #126](https://github.com/securely1g/sonic-buildimage/issues/126).

The owner builds the existing nine installed telemetry, dialout and gNMI/gNOI programs with Go 1.25.9 and exports runtime, matching debug symbols, component sources and runtime metadata. Common owns the reusable CGo binding; Management Common owns generated schemas and Go interfaces. The legacy Make producer remains available. No DEB producer is selected.

The source archive is unchanged. The registry module patch sets its registered version and aligns the current native dependency minima. The independent consumer imports a public gNMI library and builds six targets, including the runtime/debug/source TARs and generated YANG server. Three owner checks inspect installed package and component-source contracts and execute telemetry/gnmi_get against private Redis fixtures. The standard optimized configuration keeps empty global Go tags. Source CI separately exercises `fastbuild --strip=always` and a failing host-BFD canary, the original suites and CodeQL.

The current ordinary consumer selects the accepted native dependencies from one complete review catalog:

| Dependency | Selected input | Registration |
| --- | --- | --- |
| SWSS Common | `0.0.8-43598143ef4a46431eae0859915cd7d951dad1ed` | [#201](https://github.com/securely1g/sonic-bazel-registry/pull/201) |
| Build infrastructure | `0.0.26-2cfc059c2cf1dc3b2f2b2ec1bcd70400b04ecb75` | [#209](https://github.com/securely1g/sonic-bazel-registry/pull/209) |
| Management Common | `1.0.0-f5361ba8b88cde7ec59bdb4652a986c68d66da64` | [#165](https://github.com/securely1g/sonic-bazel-registry/pull/165) |
| libnl | `3.7.0.sonic.7` | [#181](https://github.com/securely1g/sonic-bazel-registry/pull/181) |
| Distroless | published `0.9.4.sonic.16` | [#200](https://github.com/securely1g/sonic-bazel-registry/pull/200) |

The registered module and source MODULE patch declare the current Common, infrastructure and Management Common minima. The ordinary consumer resolves these candidates without module or local source overrides. The Go 1.25.9 SDK, `rules_go@0.64.1-sonic.1`, original feature patches, six build targets and three installed tests remain unchanged. Fresh acceptance of this updated consumer is pending; earlier results do not establish this new graph's runtime behavior.

This is the first gNMI registration. The native AMD64 Trixie scope does not include ARM, ASAN or a full VS installer. Keep Draft while required sources and registrations remain unlanded and this PR uses a stacked review base. The source prerequisites are [gNMI #2](https://github.com/securely1g/sonic-gnmi/pull/2) and its counter-fix [#1](https://github.com/securely1g/sonic-gnmi/pull/1).

Earlier acceptance used the catalog supplied by [registry #180](https://github.com/securely1g/sonic-bazel-registry/pull/180), including Common [#167](https://github.com/securely1g/sonic-bazel-registry/pull/167), infrastructure [#179](https://github.com/securely1g/sonic-bazel-registry/pull/179), tar [#174](https://github.com/securely1g/sonic-bazel-registry/pull/174) and Distroless [#177](https://github.com/securely1g/sonic-bazel-registry/pull/177). Those historical inputs are preserved in the earlier receipts; the current consumer above is validated separately.

The registration and ordinary consumer now use Management Common `1.0.0-20afb37991752fb83f2f79cc3c9c3377636d34ce` with the public `openconfig_goyang` and `openconfig_ygot` modules from registry PRs #212/#214/#216. Their duplicated Go patch overrides are removed; the original gNMI source, Go 1.25.9, rules_go 0.64.1, unrelated Go patches and all six build/three test targets remain. Actual ordinary-consumer acceptance on this graph is pending.

The combined Framework review graph adds a standard `go.bazel.work` replacement for `golang.org/x/text v0.39.0`, already required by both source owners and Management Common. This prevents the rules_go 0.65 build-tool graph from selecting x/text 0.42, which requires Go 1.26, while the source SDK remains Go 1.25.9. The gNMI producer source and other runtime selections are unchanged; cumulative Framework/gNMI graph acceptance remains pending.

The shared Go 1.25.9 root also preserves `golang.org/x/sync v0.21.0`, the exact existing gNMI owner requirement. The rules_go tool graph otherwise raises it to v0.23.0 (Go 1.26), and the actual combined image audit reaches it through ORAS semaphore. This changes only the standard root workspace replacement and its integrity; no application source, source revision, SDK, original patch, test target or OTEL private module graph changes. The separate full image audit and runtime checks remain required.
