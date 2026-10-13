# SWIG feature definitions

Registers [infrastructure #44](https://github.com/securely1g/sonic-build-infra/pull/44)
for [Common #23](https://github.com/securely1g/sonic-swss-common/pull/23).
Both Python and Go SWIG rules accept `defines`, so Common can select its YANG
interface directly and remove its generated interface adapter.

Native AMD64/ARM64 registry validation checks real generated wrappers with
bare and valued definitions, default interfaces, the Python native-library
helper, and matching runtime/debug TAR generation. No selected target
produces a DEB. The module-identity patch leaves the implementation unchanged.
