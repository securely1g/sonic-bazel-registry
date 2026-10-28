# Native Net-SNMP Bazel registration

Builds Net-SNMP libraries, agents, tools and Perl bindings with native Bazel rules. Public `*_layout` targets provide OCI installation TARs, with matching `*_elf.debug_symbols` TARs. The AMD64 and ARM64 target platforms use Debian Bookworm user-space dependencies. Final DEB assembly and package-manager maintenance scripts are outside this registration.

Both architectures include `snmppcap`, using the declared libpcap dependency. Upstream enables this command when libpcap is available; it has no CPU restriction. `package_contract_test` checks all 22 commands, two daemons, six shared libraries and seven Perl bindings in the delivered TARs, including permissions, architecture and matching build IDs/debug-link checksums. These archive checks complement the feature/ABI test; they do not establish live SNMP service behavior.

## Native Draft validation prerequisites

The net-snmp candidate uses infrastructure `0.0.25-1341eaf4a7759ef0121ae7c17edcd0000d063038` from [registry #147](https://github.com/securely1g/sonic-bazel-registry/pull/147) and the `.13` library exports from [#146](https://github.com/securely1g/sonic-bazel-registry/pull/146). This infrastructure supplies the shared Bookworm execution-tool set and corrected packaged Python extension lookup.

Its native CI stages only those exact prerequisite recipes and libnl3 from #148 from the immutable Draft catalog pinned by [this PR’s workflow](../../../.github/workflows/registry-ci.yml); the PR's own `net-snmp@5.9.3.sonic.1` recipe stays under test. The runner uses that single local catalog plus BCR, and retains `draft-prerequisites.json` with the exact entry trees. This is temporary validation, not a published dependency or a Ready criterion. Remove the staging step and verify maintained-main resolution after the prerequisites land.

| Input or action | Before | After |
| --- | --- | --- |
| Native net-snmp registry validation for FRR's libraries and installation TARs | Older Draft infrastructure omits the reviewed execution-tool fixes | The reviewed `0.0.25-1341eaf4…` recipe supplies the shared Bookworm tools and Python extension lookup; `.13` provides the required APT library targets |

For local reproduction, stage the same entry trees from the pinned catalog into a disposable registry worktree, preserving this candidate, then run its existing `ci/registry_ci.py run --module net-snmp --version 5.9.3.sonic.1` command for the native architecture. Published module entries in the PR remain unchanged; historical cross-build results do not establish native ARM64 execution.
