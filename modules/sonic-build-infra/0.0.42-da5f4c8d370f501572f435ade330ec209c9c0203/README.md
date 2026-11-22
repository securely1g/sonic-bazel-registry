# Debian package tar compatibility

This release registers commit `da5f4c8d370f501572f435ade330ec209c9c0203` from [Infra #130](https://github.com/securely1g/sonic-build-infra/pull/130).

The shared Debian package assembler writes tar headers accepted by dpkg for
long payload names and link targets. Kernel debug packages exercise these
paths when installed on Debian Trixie. The registry presubmit runs
the dpkg unpack regression and assembler tests on AMD64 and ARM64 alongside
the existing compiler, runtime and packaging checks.
