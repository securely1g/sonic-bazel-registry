# Native FIPS runtime packages

This candidate registers source composition `dcd6a3a1ba873386b1f80d5b0b1f96a23728b399` as `0.0.2-dcd6a3a1ba873386b1f80d5b0b1f96a23728b399`.
The source archive and module patch are checksum pinned. The patch sets the
registry version. The source selects the reviewed build infrastructure candidate `72d9705e37d0e83a072cad3eb73b75cd6cc1e4c6`
and the consolidated Distroless `0.9.4.sonic.5` fixes.

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

This Draft registration temporarily targets [registry #80](https://github.com/securely1g/sonic-bazel-registry/pull/80)
so its validation catalog contains the new pinned Debian GCC toolchains. Retarget
to maintained `main` after #80 merges. The source retains the shared
`@sonic_sysroot` API and declares the GNU launchers' Debian runtime files in the
Clang-specific SymCrypt build. Ordinary consumer registry endpoints remain SONiC
main plus BCR. The composed source features remain unlanded.
