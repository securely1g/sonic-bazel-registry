# DASH HA native AMD64 source producer

This initial registration packages landed DASH HA master commit
`502377912f3530c9bb6c27007822919f6f32aeb7` from
[source PR #1](https://github.com/securely1g/sonic-dash-ha/pull/1).
The source owns all 14 Cargo workspace crates, the original protocol generators,
Cargo.lock, native installation layout, and its build and test rules.
The registry patch only sets the commit-qualified module version.

## Public outputs and tests

The native Debian Trixie AMD64 consumer builds:

- `@sonic-dash-ha//:dash_ha_pkg`: hamgrd, swbusd, swbus-cli, and wait_for_loopback.py.
- `@sonic-dash-ha//:dash_ha_pkg.debug_symbols`: matching separate debug symbols.
- `@sonic-dash-ha//:runtime_packages.json`: source-package identity and payload metadata.
- `@sonic-dash-ha//crates/container:container`: a separate build utility.

The registered consumer retains the 19 original crate/integration test targets,
installed TAR/ELF/GDB and private-loopback SWBus acceptance, and the native
Rustdoc target for the original compile_fail and no_run examples: 21 targets.
The source CI additionally covers dev/release modes and Common's three existing
async/testing compatibility targets. Its tested merge tree is identical to the
landed source. Registry CI exercises an ordinary fresh external consumer.
The declared targets produce source TARs and metadata.

## Dependencies and consumer toolchains

The source selects published infrastructure 0.0.33, shared Rust 0.0.5-dd364f2,
Common 0.0.9-334389e, API 0.0.5-9b2893e, Distroless .18, tar.bzl .sonic.2,
and Protobuf legacy .sonic.2. Test tools consume infrastructure's shared APT
production lock. Cargo and APT input bytes remain source-owned.

The generated test root pins infrastructure, tar.bzl, rules_cc 0.2.20 and
rules_go 0.64.1 to reproduce the source root's overrides, which do not propagate
from a dependency module. Its rules_rs declaration supplies Rust 1.90.0 with
bindgen and mangled allocator libraries. Other source dependencies resolve
through the module's maintained declarations. Both target and host platforms
select native AMD64 Trixie.

The API owner supplies HA's original schema revision
`18a29c1c8a21aeb22a4893c786564acaf8212156`, preserving ha_scope_id=1 and vdpu_id=2.
Docker image integration is the separate
[buildimage PR #155](https://github.com/securely1g/sonic-buildimage/pull/155).
See [registry CI](../../../ci/README.md) for the standard fresh-consumer command.
