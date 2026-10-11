# Native FIPS runtime packages

This candidate registers source composition `6ef4c4f2e81efa4ac456f7274398c0fb16a62c24` as `0.0.2-6ef4c4f2e81efa4ac456f7274398c0fb16a62c24`.
The source archive and module patch are checksum pinned. The patch sets the
registry version and selects the consolidated Distroless `0.9.4.sonic.5` fixes.

The integration source preserves these reviewed features:

| Feature | Source commit |
| --- | --- |
| [OpenSSL #1](https://github.com/securely1g/sonic-fips/pull/1) | `3d80284735c155e49efa818640837a0b59b057b1` |
| [OpenSSH #2](https://github.com/securely1g/sonic-fips/pull/2) | `499b4d68adb325cea2fbe1b6a31b20defa6c3b72` |
| [Kerberos #3](https://github.com/securely1g/sonic-fips/pull/3) | `79f8d2242f7159bfd9590e8a971c5a6e1007e4e8` |
| [SymCrypt #4](https://github.com/securely1g/sonic-fips/pull/4) | `1e4584bc8a7faec873796090667a8132535747f0` |
| [OpenSSL vendor suite #5](https://github.com/securely1g/sonic-fips/pull/5) | `2c5c77d3f00f5429e5ebf57f013b5e0a7c999028` |

The base-image and Syncd migration consume the public runtime, development and
matching debug TARs. Native AMD64 and ARM64 presubmits build all seventeen TARs
and run the four installed-package tests plus the full OpenSSL vendor suite
with source-built SymCrypt from a separate consuming module.
They compile source code and import existing external package inputs; they do
not produce Debian packages. SymCrypt's sealed core is packaged without further
binary editing and publishes its original symbols by build ID through the shared
OCI debug-symbol provider. No cryptographic certification is claimed.

This is an integration-only draft until the source features and prerequisite
registrations land. Its temporary registry base contains exact
[Distroless #68](https://github.com/securely1g/sonic-bazel-registry/pull/68),
[build tools/compiler/sysroot #65](https://github.com/securely1g/sonic-bazel-registry/pull/65),
and [LLVM executor runtime #66](https://github.com/securely1g/sonic-bazel-registry/pull/66).
Ordinary consumer registry endpoints remain SONiC main plus BCR.
