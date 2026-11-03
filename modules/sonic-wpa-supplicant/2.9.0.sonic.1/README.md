# WPA source TARs for the MACsec image

SONiC's `docker-macsec` needs the patched WPA supplicant and its database
adapter. This entry consumes the source-owned targets from
[WPA PR #1](https://github.com/securely1g/sonic-wpa-supplicant/pull/1), which
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

The ordinary consumer declares the source module and compatible native tool
interfaces without root source or version overrides. It keeps Common's declared
YANG-enabled default. AMD64 CI builds all three
public outputs and executes the owner's upstream, installed-package and flag
preservation tests. Those tests check exact payload bytes/modes/links/epoch,
three ELF/debug pairs, real GDB lookup, declared Common/libnl/OpenSSL loading,
the IEEE PBKDF2 vector and private supplicant/control-client PING/PONG. Twelve
upstream programs compile; nine self-contained suites execute. Three HTTPS/X.509
programs have compile-only coverage because their external fixtures are absent.

The dependency chain is [Common registration #180](https://github.com/securely1g/sonic-bazel-registry/pull/180),
including the `.8-33d2790e` Common owner, [libnl #181](https://github.com/securely1g/sonic-bazel-registry/pull/181)
with `.7` native SONAME filenames, [infra #179](https://github.com/securely1g/sonic-bazel-registry/pull/179),
[public Distroless #177](https://github.com/securely1g/sonic-bazel-registry/pull/177),
and the already merged [dotted TAR #174](https://github.com/securely1g/sonic-bazel-registry/pull/174).
Keep this registration Draft while the remaining inputs and the source PR are unlanded.

The image consumer is [buildimage issue #131](https://github.com/securely1g/sonic-buildimage/issues/131).
Image assembly, an actual installed macsecmgrd/WPA handoff and full VS installer
coverage are separate from source/registry acceptance. ARM, cross builds,
physical MACsec traffic and ASIC/FIPS POST behavior are outside this phase.
