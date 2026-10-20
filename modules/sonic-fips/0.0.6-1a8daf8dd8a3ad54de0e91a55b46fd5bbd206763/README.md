# FIPS runtime and debug TARs

Register `sonic-fips@0.0.2-da444a14aea8483fcb8df84d0a049bf9db0fb15a` from the
[merged source commit](https://github.com/securely1g/sonic-fips/commit/da444a14aea8483fcb8df84d0a049bf9db0fb15a)
on maintained `main`. The source includes merged [OpenSSL #1](https://github.com/securely1g/sonic-fips/pull/1),
[OpenSSH #2](https://github.com/securely1g/sonic-fips/pull/2),
[Kerberos #3](https://github.com/securely1g/sonic-fips/pull/3),
[SymCrypt #4](https://github.com/securely1g/sonic-fips/pull/4), and
[OpenSSL vendor tests #5](https://github.com/securely1g/sonic-fips/pull/5).
The archive and module-version patch are checksum pinned.

The [base image](https://github.com/securely1g/sonic-buildimage/pull/30) and
[Syncd](https://github.com/securely1g/sonic-buildimage/pull/13) consumers use the
seventeen public runtime, development and matching debug TAR targets directly
for OCI assembly. Both currently select the earlier FIPS source `c363f13c`
through registry snapshot `9865e013`; adopting this landed version and validating
the resulting whole images remain separate consumer work.
Native AMD64 and ARM64 registry CI builds all seventeen TARs and runs the four
installed-package tests plus the OpenSSL vendor suite with source-built
SymCrypt plugins from a separate consuming module.

The source and validation consumer use landed
`sonic-build-infra@0.0.17-8baf1ad829c5095297d85148b042145b87d623a3` from
[registry #81](https://github.com/securely1g/sonic-bazel-registry/pull/81),
`rules_distroless@0.9.4.sonic.6` from
[registry #82](https://github.com/securely1g/sonic-bazel-registry/pull/82), and
`tar.bzl@0.10.5-sonic.1`. Normal registry endpoints remain SONiC main plus BCR.

These targets compile project sources and import existing external packages;
they do not produce DEBs. SymCrypt's sealed core is packaged without further
binary editing and publishes its original symbols by build ID. The OpenSSH
TAR includes the merged tmpfiles configuration. Image activation and FIPS
certification remain separate validation requirements.
