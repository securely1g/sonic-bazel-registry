# Native Net-SNMP Bazel registration

Builds Net-SNMP libraries, agents, tools and Perl bindings with native Bazel rules. Public `*_layout` targets provide OCI installation TARs, with matching `*_elf.debug_symbols` TARs. The AMD64 and ARM64 target platforms use Debian Bookworm user-space dependencies. Final DEB assembly and package-manager maintenance scripts are outside this registration.
