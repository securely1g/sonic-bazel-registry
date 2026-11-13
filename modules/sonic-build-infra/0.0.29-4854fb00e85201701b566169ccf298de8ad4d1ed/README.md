# Shared build-infra 0.0.29

This entry makes the Trixie AMD64 Router Advertiser runtime available as the `radv_runtime_debian` collection in the shared production APT lock. It adds `radvd:amd64=1:2.20-1+b1`. The existing 2,425 package records and 55 collections retain their contents. [Source change](https://github.com/securely1g/sonic-build-infra/pull/96)

Consumers import `@sonic_build_infra//apt:apt.lock.json` and select `radv_runtime_debian`. The existing `sysmgr_debug_debian` selection supplies the debug tools. [Router Advertiser consumer](https://github.com/securely1g/sonic-buildimage/pull/143)

The registry checks the shared lock and runs the established AMD64 and ARM64 build-infra presubmits. The Router Advertiser image workflow verifies its daemon, installed files and rendered configuration. [Registry checks](presubmit.json) · [Patch details](PATCHES.md)
