# libyang 3.12.2.sonic.10

This release adds the same parser fix used by the native SONiC build. It preserves the Debian source archive, package identity and Bazel targets from `3.12.2.sonic.9`. The registry applies both SONiC patches in the native series order. [Upstream buildimage change](https://github.com/sonic-net/sonic-buildimage/pull/30723)

Registry presubmit builds and tests the library on AMD64 and ARM64. The public library, headers and package payloads can be consumed with `bazel_dep(name = "libyang", version = "3.12.2.sonic.10")`.
