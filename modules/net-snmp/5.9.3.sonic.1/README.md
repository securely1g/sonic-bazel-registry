# Native Net-SNMP Bazel registration

Builds Net-SNMP libraries, agents, tools and Perl bindings with native Bazel rules. Public `*_layout` targets provide OCI installation TARs, with matching `*_elf.debug_symbols` TARs. The AMD64 and ARM64 target platforms use Debian Bookworm user-space dependencies. Final DEB assembly and package-manager maintenance scripts are outside this registration.

Both architectures include `snmppcap`, using the declared libpcap dependency. Upstream enables this command when libpcap is available; it has no CPU restriction. `package_contract_test` checks all 22 commands, two daemons, six shared libraries and seven Perl bindings in the delivered TARs, including permissions, architecture and matching build IDs/debug-link checksums. These archive checks complement the feature/ABI test; they do not establish live SNMP service behavior.

## Maintained native validation dependencies

The module and its generated consumer select infrastructure `0.0.25-34de7330abc72229dfc8dab88dec71b89c52aa88` from [registry #147](https://github.com/securely1g/sonic-bazel-registry/pull/147) and `libnl3@3.7.0.sonic.7` from [#181](https://github.com/securely1g/sonic-bazel-registry/pull/181). Infrastructure requires Distroless `0.9.4.sonic.15`, including the native exports and public `cc_import` compatibility landed through [#146](https://github.com/securely1g/sonic-bazel-registry/pull/146) and [#177](https://github.com/securely1g/sonic-bazel-registry/pull/177). These registrations are present in maintained registry main; validation no longer restores prerequisite recipes from a separate Draft catalog.

| Validation input | Previous behavior | Resulting behavior |
| --- | --- | --- |
| Native Net-SNMP dependencies | CI restored three exact patched Draft recipes before validation | The declared maintained versions supply the same required native and Bookworm interfaces through the normal registry path |

Net-SNMP source archives, all 48 patches, public target names, the 16 TAR build targets, two contract tests and supported AMD64/ARM64 Bookworm matrix remain unchanged. The maintained prerequisites include libnl SONAME/SDK timestamp fixes and an infrastructure debug TAR mode correction; old and new TAR bytes are not claimed equivalent. Historical native and artifact results at `1a625e0d` retain their original dependency attribution. This maintained closure still needs current native CI and artifact validation.

The main workflow uses the maintained reusable module job and runner routes. On the exact `pr/frr-net-snmp` Draft branch, the existing two package-generating kernel fixture tests are excluded from the broader automatic module selection. All build targets, remaining tests and default coverage on other branches are preserved. This is not full kernel test acceptance; remove the temporary exclusion before Ready. No DEB generation, live SNMP/FRR service, image, installer or guest-boot acceptance is claimed.
