## Registry dependency refresh: `0.1.1-9941c86ae87437894fb76f3c10a0db863ba4d289`

Source: `securely1g/sonic-dhcpmon@9941c86ae87437894fb76f3c10a0db863ba4d289`, based on `7ef86d9cf0fa3a6adf9be8dd17ad8bb49708d8a9`. Dependency targets are frozen to published registry snapshot `3d1cc5e8dfd553d2acbe4198e504a245e6bdbddf`. The source owns the module base version and dependency updates. The registry supplies the full commit-qualified identity and retains its existing integration behavior.

Full archive patch-application and build validation must be recorded separately.

# SONiC DHCP monitor

This entry registers [the landed DHCP monitor source](https://github.com/securely1g/sonic-dhcpmon/commit/b824589b2ba49a8ba59142289bfb04bb3ca68875).
The source repository owns the build, runtime packaging, Debian metadata, and behavior tests.
The only registry patch sets the module version to `0.1.0-b824589b2ba49a8ba59142289bfb04bb3ca68875`.

Both native Debian Trixie presubmits build the runtime and detached debug symbols
(`//:runtime` and `//:runtime.debug_symbols`), generate Debian metadata
(`//:monitor_metadata`), and run the production utility test (`//:util_behavior_test`).
The module imports the `dhcpmon_debian` package set from sonic-build-infra's shared
APT lock. The consumer selects the same build infrastructure, toolchains, and packaging
rules as the source build. Each native runner obtains the test launcher from the existing
checksum-verified Cosmos manifest.
