# Native libnl3 source build

FRR links `libnl_3` and `libnl_route_3`; config-engine consumes
`libnl-3-runtime_files` and `runtime_packages.json`. This update keeps
`3.7.0.sonic.6` and its original Debian 3.7.0 archive URL and SHA-256. At the
user's explicit request, it patches this published entry in place instead of
adding `.7`. Registry CI permits only the recorded before/after entry trees;
other published inputs remain protected.

| Input or action | Before | After |
| --- | --- | --- |
| Build libnl3 for FRR with its SONiC source fixes | Separate repository generation and parser toolchains | Shared native compiler and declared parser tools; the same runtime, SDK and debug interfaces |
| Request `libnl3@3.7.0.sonic.6` | Published build overlay | That overlay followed by `patches/0001-build-libnl3-with-shared-native-rules.patch` |

The original overlay files and nexthop patch remain intact, except for the
regenerated `MODULE.bazel`. The numbered patch updates the build definitions,
adds the remaining SONiC source fixes and package tests, and removes unused
repository-generation helpers. Bazel applies it after installing the overlays.
No new DEB producer is introduced.

## Dependencies and reproduction

[Registry #147](https://github.com/securely1g/sonic-bazel-registry/pull/147)
patches infrastructure `0.0.25-17a1e555291c64be1a6ff008f33352bffc4f8e5c` with the
shared Bookworm execution tools and native runtime fixes.
[Registry #146](https://github.com/securely1g/sonic-bazel-registry/pull/146)
supplies the Distroless `.13` library exports. Draft CI stages those exact
prerequisite trees from the immutable catalog recorded in the workflow and
retains `draft-prerequisites.json`. This PR's libnl3 entry remains under test.
Remove temporary staging and verify maintained-main resolution after those
prerequisites land.

`MODULE.bazel` is the maintained module definition. After editing it, update
and check its generated overlay:

```sh
python3 ci/registry_ci.py sync-module --module libnl3 --version 3.7.0.sonic.6
python3 ci/registry_ci.py sync-module --module libnl3 --version 3.7.0.sonic.6 --check
```

Reproduce native validation in the pinned CI container, with the same
prerequisite recipes staged into a disposable registry checkout:

```sh
python3 ci/registry_ci.py run --module libnl3 --version 3.7.0.sonic.6 \
  --architecture amd64 --work-dir /tmp/libnl3-ci --artifacts /tmp/libnl3-evidence
python3 modules/libnl3/3.7.0.sonic.6/tests/installed_sdk_test.py \
  --artifacts /tmp/libnl3-evidence
python3 modules/libnl3/3.7.0.sonic.6/tests/installed_debug_test.py \
  --artifacts /tmp/libnl3-evidence
```

Use `--architecture arm64` on a native ARM64 runner. Cross-built archive
inspection does not establish native consumer execution.

## Installation and regression coverage

Runtime targets ship five libraries, ten CLI plugins and configuration files;
core and route development targets separately ship headers, static archives,
linker symlinks and pkg-config data. Libraries use `/usr/lib/<multiarch>` and
configuration uses `/etc/libnl-3`. Existing aggregate SDK targets remain
available. Runtime package metadata comes from the pinned Debian packaging
and the built files.

The existing native AMD64/ARM64 matrix builds all libraries, utilities,
metadata and runtime/debug TARs. Tests check exact split inventories, ownership,
modes, symlinks, architecture, SONAMEs, build IDs, debug-link CRCs and DWARF
separation for every library and plugin. Post-build checks verify output
checksums, compile and run shared and whole-archive SDK consumers, require
loaded libraries to come from the extracted packages, and locate source lines
with GDB using only the matching delivered symbols. Receipts and logs remain
with the artifacts. Full FRR/config-engine image validation is separate.
