# Sairedis SAI code generation

This version registers Sairedis master commit `33443ea1666a23812365d03fb959066ee84c9aa0`. Its SAI stub generator runs Python on the build host, so an AMD64 runner can generate Redis, VS and Proxy SAI C++ sources for ARM64. For example, the build executes AMD64 Python and compiles the generated VS stub with AArch64 GCC. [SAI stub generator](https://github.com/securely1g/sonic-sairedis/pull/10)

The source archive includes the ZeroMQ and Syncd log format corrections and the ZeroMQ poller shutdown fix. The pending-request test tears down a channel with an unread request, rebinds its endpoint and checks a second request and reply. The registry applies one patch to record the exact module version and retain the gzip toolchain used by package consumers. [ZeroMQ log formats](https://github.com/securely1g/sonic-sairedis/pull/11) · [Syncd and saidump log formats](https://github.com/securely1g/sonic-sairedis/pull/12) · [ZeroMQ shutdown and regression test](https://github.com/securely1g/sonic-sairedis/pull/13)

The AMD64 and ARM64 presubmits retain all 19 build targets and seven tests from published version 0.0.4.
