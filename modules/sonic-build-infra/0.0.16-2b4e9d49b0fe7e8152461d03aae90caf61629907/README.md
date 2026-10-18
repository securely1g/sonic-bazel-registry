# Debian source package producer tools

This draft registration lets the separate source-package PRs for buildimage
[#33](https://github.com/securely1g/sonic-buildimage/pull/33) consume one exact
infrastructure snapshot during native AMD64/ARM64 validation.

The snapshot combines the control-file support from infra
[#45](https://github.com/securely1g/sonic-build-infra/pull/45), pinned dpkg tools
from [#46](https://github.com/securely1g/sonic-build-infra/pull/46), original
Debian maintainer helpers from
[#47](https://github.com/securely1g/sonic-build-infra/pull/47), the shared
`debian_metadata`/`debian_library` producer rules from [#48](https://github.com/securely1g/sonic-build-infra/pull/48), and the existing Kerberos
build tools and sysroot support needed by FIPS source builds.

The source is the integration branch's exact commit; it is not a landed main
commit. Keep this registration and consumers Draft until their dependencies
land and their pins are refreshed. The component PRs retain ownership of
payload compilation, original Debian inputs, and package installation tests.
