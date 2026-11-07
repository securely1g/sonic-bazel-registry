# Management Framework runtime and CLI TARs

Register public Framework commit `2e6bb6b7ef3327094e4f5e02f2273f3c7e2838a5` from [source #1](https://github.com/securely1g/sonic-mgmt-framework/pull/1) for [buildimage #138](https://github.com/securely1g/sonic-buildimage/pull/138). The existing REST server, UI, generated models and klish CLI remain source-built with runtime/debug TAR interfaces; no DEB producer is selected.

| Consumer input | Before | After |
| --- | --- | --- |
| Management Common | Unlanded `1.0.0-71eb5f71...` | Maintained `1.0.1-05f83dcab8fe2e1a0e0fc37ac172b289d6968e2b` from [registry #216](https://github.com/securely1g/sonic-bazel-registry/pull/216) |
| gNMI Go workspace and public libraries | Superseded `ce49e93e...` candidate | The single `08131f87...` candidate from [registry #182](https://github.com/securely1g/sonic-bazel-registry/pull/182) |
| SWSS Common override | Unlanded `43598143...` | Published `0.0.9-334389eae54afd1f4f5ee69f89c3a7ad2062ee61` |
| Framework source | `4036a01a...` | Verified `2e6bb6b7ef3327094e4f5e02f2273f3c7e2838a5`, whose source root selects the landed shared owners |

The producer registration retains its existing infrastructure `.25-3ee15ec9` recipe. The separate consumer selects maintained Common9 and infrastructure `.26-51c838da` to match the current gNMI source graph, while retaining `rules_go@0.65.0.sonic.1`, Distroless `.16`, Go 1.25.9 and the consuming gNMI Go workspace. The adapted MODULE-only patch keeps non-root `go.mod` discovery and the existing published infrastructure selection. It no longer duplicates source changes that already adopt Management Common, goyang and ygot. The source root's separate CLI override remains part of source #1; this registry patch continues using its existing maintained infrastructure entry.

All seven build targets and ten tests are unchanged, including REST runtime, package contracts, installed CLI, model/codegen reproducibility, server/OpenAPI fixtures and CLI/TLS tests. The source archive's 276 Git blobs and modes were checked in full. Source `2e6` normal CI passed, including native Framework and CodeQL; this does not establish acceptance of the registry consumer's distinct non-root graph. Current registry and downstream-image validation are pending. gNMI's Actions workflows resumed after enablement. Its CodeQL vendor handoff is repaired in source `08131f87`; current source, consumer and image acceptance remain separate requirements.

Keep Draft until the exact source and gNMI prerequisite registrations land and current consumer validation passes. This native AMD64 Trixie registration does not claim ARM or VS installer acceptance.
