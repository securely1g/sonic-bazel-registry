

## Native Draft validation prerequisites

The libnl3 candidate uses infrastructure `0.0.25-1341eaf4a7759ef0121ae7c17edcd0000d063038` from [registry #147](https://github.com/securely1g/sonic-bazel-registry/pull/147) and the `.13` library exports from [#146](https://github.com/securely1g/sonic-bazel-registry/pull/146). This infrastructure supplies the shared Bookworm execution-tool set and corrected packaged Python extension lookup.

Its native CI stages only those exact prerequisite recipes from the immutable Draft catalog pinned by [this PR’s workflow](../../../.github/workflows/registry-ci.yml); the PR's own `libnl3@3.7.0.sonic.7` recipe stays under test. The runner uses that single local catalog plus BCR, and retains `draft-prerequisites.json` with the exact entry trees. This is temporary validation, not a published dependency or a Ready criterion. Remove the staging step and verify maintained-main resolution after the prerequisites land.

| Input or action | Before | After |
| --- | --- | --- |
| Native libnl3 registry validation for FRR's libraries and installation TARs | Older Draft infrastructure omits the reviewed execution-tool fixes | The reviewed `0.0.25-1341eaf4…` recipe supplies the shared Bookworm tools and Python extension lookup; `.13` provides the required APT library targets |

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
candidate CI remains required. The post-build SDK checks below separately cover
extracted shared/whole-archive execution and loaded-library origins.

## Check installed debug symbols in native CI

After the existing Bazel build and tests, the native AMD64/ARM64 workflow runs
`tests/installed_debug_test.py` with the GDB already installed in its pinned
Debian container. It verifies the retained output checksums, extracts each of
the five runtime/symbol TAR pairs, and asks GDB to locate an actual source file
and line for all five libraries and ten CLI plugins. Debuginfod and automatic
GDB scripts are disabled; only the matching extracted debug directory is used.
The JSON receipt and log are retained with the original build outputs.

| Input or action | Before | After |
| --- | --- | --- |
| Debug `libnl-route-3.so.200.26.0` used by FRR or a shipped `qdisc/plug.so` plugin | Archive metadata can match without proving GDB reads the delivered line tables | Native CI fails unless GDB resolves source and line information from the paired delivered symbols |

This is a post-build validation step, not a new tool dependency in the Bazel
producer. It does not change source recipes, published versions or TAR outputs.
Local execution against historical `.3` AMD64 and ARM64 TARs validates the GDB
checker only; ARM64 binary execution and current `.7` native CI remain separate
evidence. Run `python3 modules/libnl3/3.7.0.sonic.7/tests/installed_debug_test.py
--artifacts <retained-ci-artifacts>` in a validation environment with GDB.

## Exercise the installed SDK and runtime

Native CI runs `tests/installed_sdk_test.py` using the compiler, binutils and
Python already installed in the validation container. It verifies the retained
TAR checksums, extracts the core/route development files with the five runtime
packages, and compiles two consumers against those files: the inherited socket,
link and `ip.src` configuration lookup, and SONiC's route next-hop regression.
Each consumer runs once with shared libraries and once with every member of the
core and route static archives linked. The static executables must not depend on
libnl shared libraries; the shared SONiC consumer verifies their extracted origin.

| Input or action | Before | After |
| --- | --- | --- |
| Link FRR's core/route SDK with `--whole-archive` | File inventories alone cannot detect missing parser objects or duplicate library members | Compile and run both consumers using every object from the delivered static archives |
| Load `libnl-cli-3` and its ten CLI plugins | A valid ELF/archive does not establish that every symbol resolves or that the installed library is used | Load all five libraries and ten plugins with immediate symbol resolution and require every mapped libnl path to be inside the extracted package tree |

Local native AMD64 validation passed all four consumer executions and all 15
library/plugin loads against retained historical SONiC `.3` TARs. It rejected
missing and unresolved plugins, an empty static archive, a library loaded from
outside the extracted tree, and a mismatched native architecture. These are
checker tests, not new `.7` producer builds; current native AMD64/ARM64 CI and
full FRR/config-engine image integration remain separate validation. No source
recipe, published version or Bazel tool dependency changes. Reproduce with
`python3 modules/libnl3/3.7.0.sonic.7/tests/installed_sdk_test.py --artifacts
<retained-ci-artifacts>` in the native validation container. Its JSON receipt
and log are retained alongside the build outputs.
