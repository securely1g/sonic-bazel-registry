# Native Net-SNMP Bazel registration

Builds Net-SNMP libraries, agents, tools and Perl bindings with native Bazel rules. Public `*_layout` targets provide OCI installation TARs, with matching `*_elf.debug_symbols` TARs. The AMD64 and ARM64 target platforms use Debian Bookworm user-space dependencies. Final DEB assembly and package-manager maintenance scripts are outside this registration.

Both architectures include `snmppcap`, using the declared libpcap dependency. Upstream enables this command when libpcap is available; it has no CPU restriction. `package_contract_test` checks all 22 commands, two daemons, six shared libraries and seven Perl bindings in the delivered TARs, including permissions, architecture and matching build IDs/debug-link checksums. These archive checks complement the feature/ABI test; they do not establish live SNMP service behavior.

## Published dependencies

The module selects infrastructure `0.0.25-34de7330abc72229dfc8dab88dec71b89c52aa88`
landed by [registry #147](https://github.com/securely1g/sonic-bazel-registry/pull/147),
which selects Distroless `0.9.4.sonic.15`, and published libnl3 `3.7.0.sonic.7`.
These maintained registry entries replace the old Draft dependency catalog.
Registry CI uses the maintained reusable native AMD64 and ARM64 workflow without
staging prerequisite recipes. Published dependency entries remain unchanged.

Run `python3 ci/registry_ci.py run --module net-snmp --version 5.9.3.sonic.1
--architecture amd64 --work-dir /tmp/net-snmp-work --artifacts /tmp/net-snmp-results`
from the registry checkout to validate an independent consumer; use `arm64` on a
native ARM64 host.
