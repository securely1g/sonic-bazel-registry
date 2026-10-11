# Shared SONiC Rust dependencies

Version `0.0.3-0cae1ca73ed21c96d0022115a50e40cef3507071` adds the Rust
supervisor listener's polling, process/signal, syslog and test-injection
requirements to the existing shared graph. It preserves all existing package
versions and checksums and adds only nix 0.27.1, syslog-tracing 0.3.1 and the
component's pinned injectorpp Git revision.

Source prerequisite: [sonic-build-infra #35](https://github.com/securely1g/sonic-build-infra/pull/35).
This entry stays Draft until that source lands and its provenance is refreshed.
The independent native AMD64 and ARM64 consumers run the existing Serde and
tracing checks plus the new pipe/injector/syslog test. Existing published
version directories are unchanged.
