# Shared Trixie APT collections for MACsec and DASH HA

Extend [registry #316](https://github.com/securely1g/sonic-bazel-registry/pull/316)'s single unpublished infrastructure candidate with `macsec_debian` for [docker-macsec #149](https://github.com/securely1g/sonic-buildimage/pull/149). Preserve the three DASH HA collections used by [buildimage #155](https://github.com/securely1g/sonic-buildimage/pull/155). The registered version is `0.0.36-3070359b148ad6ad4eab749f5143ff2a38c980df`.

The archive selects the maintained integration of [source #104](https://github.com/securely1g/sonic-build-infra/pull/104), following [source #103](https://github.com/securely1g/sonic-build-infra/pull/103). The shared lock contains 73 collections and 2,453 package records.

The module declaration and version-alignment patch are generated from the exact source archive. The cross-test visibility patch, registry overlays and complete native AMD64/ARM64 presubmit matrix are unchanged. The AMD64 image collections have 3 runtime, 103 debug and 40 installed-test packages for DASH HA, plus 36 runtime packages for MACsec. Registry presubmits retain the existing infrastructure targets; image-specific collection consumption is covered by the respective image PRs.
