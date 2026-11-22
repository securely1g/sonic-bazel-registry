# Native Host Services installation inputs

Registers the merged source from [Host Services #3](https://github.com/securely1g/sonic-host-services/pull/3). Only the module version is patched.

The sonic-buildimage target `//tools/bazel/image/vs:sonic-vs.bin` consumes the Python, data and Rust runtime archives, matching Rust debug symbols, and Debian package metadata directly. The consumer configuration selects the registered Infra, libnl3 and libyang versions used by buildimage, plus the declared Rust and bindgen toolchains. AMD64 tests exercise the original installation declarations and public Common C ABI/Serde contract.
