# Trixie SNMP image APT collections

Register `sonic-build-infra@0.0.34-a4723268cd72a573ed316ab75347e698cc3f86ab` for [buildimage #134](https://github.com/securely1g/sonic-buildimage/pull/134). [Infrastructure #101](https://github.com/securely1g/sonic-build-infra/pull/101) defines the native AMD64 runtime, debug and private Redis test collections. All three retain the suites, package versions, hashes and dependency edges from the image’s original lock. The runtime includes Debian Trixie’s `snmp` and `snmpd` at `5.9.4+dfsg-2+deb13u1`.

The pinned source archive supplies the shared lock and build definitions. The version patch sets the registered module identity. The cross-test visibility patch, test overlays and native AMD64/ARM64 presubmit targets carry forward from the preceding publication.
