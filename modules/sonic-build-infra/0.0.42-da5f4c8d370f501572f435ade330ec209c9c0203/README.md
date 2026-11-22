# Kernel compatibility ELF payloads

Register merged [Infra #129](https://github.com/securely1g/sonic-build-infra/pull/129)
source `edab3bd22b7a9a2ae631f06a1a5072b113045fe7` as
`0.0.41-edab3bd22b7a9a2ae631f06a1a5072b113045fe7`.

The sonic-linux-kernel debug package includes native and compatibility VDSOs.
The shared `sonic_deb` assembler now accepts these mixed ELF machine types while
retaining the package Architecture check against its selected target platform.
The source module base version is `0.0.41` so consumers select this fix over
published `0.0.40` snapshots.

Implementation changes come from the merged source archive. The registry retains
the existing cross-test visibility patch and validation overlay, preserves the
previous consumer tests and adds `//deb:assemble_test`. Published entries remain
unchanged. The kernel module registered alongside this entry consumes the fix.
