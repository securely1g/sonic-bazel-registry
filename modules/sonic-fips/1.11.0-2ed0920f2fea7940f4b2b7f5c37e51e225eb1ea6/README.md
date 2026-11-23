# sonic-fips native Bazel registry module

Version `1.11.0-2ed0920f2fea7940f4b2b7f5c37e51e225eb1ea6` pins
[Azure/sonic-fips](https://github.com/Azure/sonic-fips/tree/2ed0920f2fea7940f4b2b7f5c37e51e225eb1ea6)
at commit `2ed0920f2fea7940f4b2b7f5c37e51e225eb1ea6`.
The implementation lives directly in this registry entry's overlay. Source
preparation preserves the original gitlinks, Debian patches and SONiC patches.
Explicit Bazel rules perform generation, compilation, linking and installation;
configure probes supply migration-time configuration data.

## Six components and 27 packages

| Component | Debian version | Public packages |
| --- | --- | --- |
| `symcrypt` | `1.11.0` | `symcrypt-openssl` |
| `openssl` | `3.5.7-1~deb13u2+fips` | `libssl3t64`, `openssl`, `libssl-dev`, `libssl-doc` |
| `openssh` | `1:10.0p1-7+fips` | `openssh-client`, `openssh-server`, `openssh-sftp-server`, `ssh` |
| `krb5` | `1.21.3-5+fips` | `libkrb5support0`, `libk5crypto3`, `libkrb5-3`, `libgssapi-krb5-2`, `libgssrpc4t64`, `libkadm5clnt-mit12`, `libkadm5srv-mit12`, `krb5-multidev`, `libkrb5-dev` |
| `python` | `3.13.5-2+fips` | `python3.13-minimal`, `libpython3.13-minimal`, `libpython3.13-stdlib`, `libpython3.13`, `python3.13` |
| `golang` | `1.26.5-1~bpo13+1+fips` | `golang-1.26-go`, `golang-1.26-src`, `golang-1.26-doc`, `golang-1.26` |

## Public interfaces

`@sonic-fips//<component>:<package>.runtime` produces the installation TAR.
`<package>.runtime_metadata` supplies the Debian control fields, dependencies and
maintenance attachments. Packages with applicable ELF symbols expose
`<package>.runtime.debug_symbols`. The root target
`@sonic-fips//:runtime_packages.json` aggregates all 27 packages.

The module uses the same generation, compilation, linking and installation rules
for AMD64 and ARM64. The selected target platform determines the toolchain,
configuration, ABI and installation paths; generation tools use the execution
configuration. For example:

```sh
bazel build \
  --host_platform=@sonic_build_infra//platforms:x86_64_trixie \
  --platforms=@sonic_build_infra//platforms:x86_64_trixie \
  @sonic-fips//openssl:openssl.runtime

bazel build \
  --host_platform=@sonic_build_infra//platforms:x86_64_trixie \
  --platforms=@sonic_build_infra//platforms:aarch64_trixie \
  @sonic-fips//openssh:openssh-server.runtime
```

Public C/C++ providers include `//openssl:libcrypto`, `//openssl:libssl`,
`//krb5:krb5` and `//krb5:gssapi`.

## Original production contracts

The package selection follows the pinned component Makefiles and Debian rules.
In particular, the SONiC consumer chain is `rules/sonic-fips.mk` → `slave.mk` →
`files/build_templates/sonic_debian_extension.j2`. Python's source selection
comes from `rules/python.mk` (`src/cpython` and `src/python3/debian`) and the
root `Makefile` in the pinned source.

CPython preserves the original module selection and five-package installation
split. GDBM and Tk remain internal build inputs where required by the original
profile workload. The static interpreter retains the original profile-guided
optimization (PGO) workload and training loop. As in the original Debian rules,
PGO runs when host and build architectures match; cross compilation retains
link-time optimization (LTO). The shared library retains its original non-PGO
configuration. DTrace generation and PGO execution use declared tool and data
inputs.

OpenSSH preserves its runit layout, permissions and maintenance script fragments.
Kerberos preserves the production libraries, headers and original plugin-symbol
exclusions. Go preserves its source-package ELF fixtures and original release
symbol settings. SymCrypt and OpenSSL retain their original installed library
and plugin contracts.

## Presubmit scope

`presubmit.json` declares 72 production build interfaces: 54 installation TAR
and metadata targets, 17 debug-symbol targets, and one root metadata aggregate.
It also declares two existing upstream smoke tests:

- `@sonic-fips//krb5:support_test_base64`
- `@sonic-fips//openssh:unit_sshkey_test`

These smoke tests exercise the Kerberos support library and SSH key/crypto
interfaces with their original inputs and assertions. Native CPython PGO
training remains a production dependency, subject to the host/build condition
above. Build and test results are reported by CI for the exact pinned dependency
versions and source archive recorded in this entry.
