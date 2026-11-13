# SONiC DHCP monitor

This entry registers [the landed DHCP monitor source](https://github.com/securely1g/sonic-dhcpmon/commit/b824589b2ba49a8ba59142289bfb04bb3ca68875).
The source repository owns the build, runtime packaging, Debian metadata, and behavior tests.
The only registry patch sets the module version to `0.1.0-b824589b2ba49a8ba59142289bfb04bb3ca68875`.

Both native Debian Trixie presubmits build the runtime and detached debug symbols
(`//:runtime` and `//:runtime.debug_symbols`), generate Debian metadata
(`//:monitor_metadata`), and run the production utility test (`//:util_behavior_test`).
The module imports the `dhcpmon_debian` package set from sonic-build-infra's shared
APT lock. The consumer selects the same build infrastructure, toolchains, and packaging
rules as the source build.
