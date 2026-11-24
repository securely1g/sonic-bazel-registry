# Shared Rust dependencies for Host Services

Host Services uses the fallible process API in sysinfo 0.40.3, procfs 0.18.0 and regex 1.13.1. The original sysinfo and procfs labels continue to select their previous versions. Both architecture checks compile the new aliases with Rust 1.95 and exercise live process lookups in the test process. [Source change](https://github.com/securely1g/sonic-build-infra/pull/138)
