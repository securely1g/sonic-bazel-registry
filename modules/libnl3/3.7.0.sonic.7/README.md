

## Native Draft validation prerequisites

The libnl3 candidate uses infrastructure `0.0.25-6f6658865b7f687fa5e78d1675c0db8a5765b2ce` from [registry #147](https://github.com/securely1g/sonic-bazel-registry/pull/147) and the `.13` library exports from [#146](https://github.com/securely1g/sonic-bazel-registry/pull/146). The superseded `f27d1bc8` candidate and removed `.14` request prevented CI from reaching compilation.

Its native CI stages only those exact prerequisite recipes from [reviewed Draft catalog `41d98ae02d50`](https://github.com/securely1g/sonic-bazel-registry/commit/41d98ae02d50c83a5575e76992294d24db70028d); the PR's own `libnl3@3.7.0.sonic.7` recipe stays under test. The runner uses that single local catalog plus BCR, and retains `draft-prerequisites.json` with the exact entry trees. This is temporary validation, not a published dependency or a Ready criterion. Remove the staging step and verify maintained-main resolution after the prerequisites land.

| Input or action | Before | After |
| --- | --- | --- |
| Native libnl3 registry validation for FRR's libraries and installation TARs | Infrastructure `0.0.25-f27d1bc8…` cannot resolve; compilation does not start | The reviewed `0.0.25-6f665886…` recipe and `.13` exports resolve from one explicit Draft catalog before the unchanged build/test target set |

For local reproduction, stage the same entry trees from the pinned catalog into a disposable registry worktree, preserving this candidate, then run its existing `ci/registry_ci.py run --module libnl3 --version 3.7.0.sonic.7` command for the native architecture. Published module entries in the PR remain unchanged; historical cross-build results do not establish native ARM64 execution.

## Preserve the installation archive regressions

Config-engine consumes `@libnl3//:libnl-3-runtime_files` with its package metadata;
FRR links the core and route libraries. `libnl3_package_test` now inspects the
exact runtime and development TARs separately from the legacy aggregate SDKs.
It retains the published `.6` file inventories and verifies all five libraries
and ten CLI plugins against their own detached debug files using declared ELF
inspection. No host `readelf` or `objcopy` is used by this checker.

| Input or action | Before | After |
| --- | --- | --- |
| Omit `usr/include/libnl3/netlink/version.h` or the `qdisc/plug.so` CLI plugin | Aggregate-only checks can miss the omitted exact-split file | The exact development/runtime inventory rejects the archive |
| Mix the `libnl-3.so.200.26.0` runtime with another debug payload | A nonempty set of debug build IDs can pass | Each runtime library and plugin must match its detached build ID, debug-link name and CRC, with DWARF only in the debug file |

Local checker validation used retained historical SONiC `.3` AMD64 and ARM64
archives: all 30 ELF pairs passed; 16 altered archives were rejected for missing
files, wrong permissions or symlinks, wrong architecture, or damaged debug data.
This validates the checker against real TARs, not a new native `.7` build. Native
candidate CI remains required. Extracted shared/whole-archive SDK execution,
loaded-library origin and GDB source-line regressions still need restoration;
these archive checks do not establish that remaining coverage.
