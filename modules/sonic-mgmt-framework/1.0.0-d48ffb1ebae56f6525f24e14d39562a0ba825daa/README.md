# Management Framework runtime and debug TARs

This module registers Framework revision `d48ffb1ebae56f6525f24e14d39562a0ba825daa` from merged [source PR #1](https://github.com/securely1g/sonic-mgmt-framework/pull/1) for [buildimage #138](https://github.com/securely1g/sonic-buildimage/pull/138). It exposes the native AMD64 Trixie REST, UI, generated models and klish CLI payloads. The runtime and debug TARs come from the same source build.

Framework and the consumer select the published build-infra 0.0.28 and Distroless 0.9.4.sonic.18. The shared Framework CLI SDK provides all 94 original package identities and the execution runtime supplies GNU patch, xmllint and xsltproc. The registry patch adapts the module version, aligns consumer `rules_go` with registry-tested `0.65.0.sonic.1` (overridden by root `single_version_override` in downstream images), and lets the consuming gNMI workspace select the shared Go graph through Framework’s go.mod.

The independent consumer uses published Management Common and gNMI. Its seven build targets and ten tests cover the TARs, REST and CLI execution, model generation, TLS and package contracts.
