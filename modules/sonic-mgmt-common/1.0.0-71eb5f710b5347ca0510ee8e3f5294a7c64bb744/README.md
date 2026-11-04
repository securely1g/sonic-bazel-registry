# Management Common with stable documentation discovery

This cumulative source preserves the accepted shared goyang/ygot ownership from
Management Common source #3 and adds source #4's deterministic YANG discovery.
The public text and HTML documentation tools now retain the same module order
when directory creation order differs. Runtime source, Go dependencies, library
interfaces and package recipes are unchanged from the accepted shared-owner
source. The code-generation TAR contains the deterministically rendered
documentation.

All six ordinary build outputs and four existing package/schema/binding tests
remain. The added `//tools/pyang:discovery_test` exercises the real renderer in
both discovery orders, preserving root-before-extension, explicit caller order,
module payloads and annotation behavior. The cumulative registered consumer passed
all six outputs and five tests. Its
consumer executable, CVL/translib/ocbinds libraries and runtime TAR are byte-identical
to the accepted source #3 registration. Only four rendered text/HTML documentation
files differ in the code-generation TAR; file inventory and metadata are preserved.
Current-head hosted verification and downstream image acceptance remain separate.

Sources: https://github.com/securely1g/sonic-mgmt-common/pull/3 and
https://github.com/securely1g/sonic-mgmt-common/pull/4. The selected review source
is 71eb5f710b5347ca0510ee8e3f5294a7c64bb744. Published f536 inputs remain intact, and this registration
replaces only the preceding unpublished 20afb candidate.
