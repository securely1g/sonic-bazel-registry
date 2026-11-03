# WPA source TARs for the MACsec image

SONiC's `docker-macsec` needs the patched WPA supplicant and its database
adapter. This entry consumes the source-owned targets from
[WPA PR #1](https://github.com/securely1g/sonic-wpa-supplicant/pull/1) and its
[compiler-flag fix #2](https://github.com/securely1g/sonic-wpa-supplicant/pull/2), which
compile the repository's selected source with `debian/config/wpasupplicant/linux`.
The public outputs are `wpasupplicant_pkg`, its matching `debug_symbols` output,
and `runtime_packages.json`. They include `wpa_supplicant`, `wpa_cli`,
`wpa_passphrase`, the declared service/configuration/documentation payload and
non-executable detached symbols. No DEB-producing targets are selected.

WPA is an upstream third-party project even though this patched source is kept
in a SONiC fork. The registry version is `2.9.0.sonic.1`, matching the source
module's mapping of WPA 2.9 and its existing SONiC/Debian downstream changes.
The immutable archive owns all build definitions. The registry adds no source
patch or replacement build implementation.

The ordinary consumer selects the accepted Common `.8-43598143`, infrastructure
`.26-51c838da`, FIPS `.3-e910ec22` and Distroless `.16` interfaces used by the
MACsec image. Direct version requirements select these accepted candidates;
there are no root source overrides or replacement build definitions. It keeps
Common's declared YANG-enabled default. AMD64 CI builds all three public outputs
and executes the owner's upstream, installed-package, flag-preservation and
large-include-list tests. Those tests check exact payload bytes/modes/links/epoch,
three ELF/debug pairs, real GDB lookup, declared Common/libnl/OpenSSL loading,
the IEEE PBKDF2 vector and private supplicant/control-client PING/PONG. Twelve
upstream programs compile; nine self-contained suites execute. Three HTTPS/X.509
programs have compile-only coverage because their external fixtures are absent.

The previous entry is [registration #185](https://github.com/securely1g/sonic-bazel-registry/pull/185).
This separate fix updates its sole unpublished WPA version to source commit
`d14bf3ac61597273e8940f9b14c8034568cccff7`. In
[MACsec image #149](https://github.com/securely1g/sonic-buildimage/pull/149),
133,110 bytes of ordered preprocessing flags exceeded Linux's limit before Make
could start. The owner now sources a Bash adapter through `rules_foreign_cc`'s
public tool-prefix hook and passes the same flags in GCC's response file.
The added test reproduces the original exec failure, verifies recursive C/C++
compilation with quoted values and include paths, and rejects driver options in
preprocessing flags. No validation or runtime features are removed.

This review catalog retains [libnl #181](https://github.com/securely1g/sonic-bazel-registry/pull/181),
[Common #201](https://github.com/securely1g/sonic-bazel-registry/pull/201),
[infrastructure #195](https://github.com/securely1g/sonic-bazel-registry/pull/195),
[FIPS #197](https://github.com/securely1g/sonic-bazel-registry/pull/197) and
[Distroless #200](https://github.com/securely1g/sonic-bazel-registry/pull/200).
The source owner's declared minima and the registry MODULE match these accepted
interfaces, so ordinary resolution exercises the actual larger downstream closure. Keep this registration Draft while its
source and registry prerequisites are unlanded. Every published version remains
unchanged.

The image consumer is [buildimage issue #131](https://github.com/securely1g/sonic-buildimage/issues/131).
Image assembly, an actual installed macsecmgrd/WPA handoff and full VS installer
coverage are separate from source/registry acceptance. ARM, cross builds,
physical MACsec traffic and ASIC/FIPS POST behavior are outside this phase.
