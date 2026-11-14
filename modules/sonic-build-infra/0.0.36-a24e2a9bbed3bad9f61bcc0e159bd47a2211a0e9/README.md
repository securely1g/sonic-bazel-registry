# Shared Trixie APT collections for DASH HA

Register `sonic-build-infra@0.0.36-a24e2a9bbed3bad9f61bcc0e159bd47a2211a0e9` from [infrastructure #103](https://github.com/securely1g/sonic-build-infra/pull/103) for the AMD64 DASH HA images in [sonic-buildimage #155](https://github.com/securely1g/sonic-buildimage/pull/155). The shared lock adds three collections: `dash_ha_debian` for the runtime, `dash_ha_debug_debian` for debugging tools, and `dash_ha_test_debian` for the installed test's Redis server.

The version patch sets the registered module identity. The cross-test visibility patch, registry test overlays, and native AMD64/ARM64 infrastructure presubmit targets carry forward from the preceding version.
