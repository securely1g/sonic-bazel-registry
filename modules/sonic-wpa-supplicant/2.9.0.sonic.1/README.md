# Native WPA source packages

SONiC's MACsec image consumes the patched WPA supplicant and its database
adapter through the source owner's public runtime, debug and metadata targets.
This entry registers source commit
[`51ee3efc59d897a7f2e0d198c782970e9f8bafe7`](https://github.com/securely1g/sonic-wpa-supplicant/commit/51ee3efc59d897a7f2e0d198c782970e9f8bafe7)
from [WPA #1](https://github.com/securely1g/sonic-wpa-supplicant/pull/1).
The upstream WPA 2.9 source and SONiC/Debian changes retain the existing
`2.9.0.sonic.1` module version.

WPA's owner compiles the three programs with native C/C++ rules, preserving
the selected `debian/config/wpasupplicant/linux` configuration and the Linux
and SONiC MACsec drivers. Common, patched libnl and OpenSSL come from their
registered owners. The FIPS owner's maintained OpenSSL producer retains its
existing build method.

The immutable source archive owns the producer and tests. Its complete
`MODULE.bazel` is registered unchanged. The consumer selects the same published
infrastructure `.34-a4723268`, Common `.9-334389ea`, FIPS `.6-18a778db`, libnl
`.7` and Distroless `.18` inputs. Its independent root also declares the Rust
1.90 toolchain used by Common's interface.

## Public outputs and validation

AMD64 registry CI builds these source-owned targets:

- `@sonic-wpa-supplicant//:wpasupplicant_pkg`
- `@sonic-wpa-supplicant//:wpasupplicant_pkg.debug_symbols`
- `@sonic-wpa-supplicant//:runtime_packages.json`

The runtime TAR includes `wpa_supplicant`, `wpa_cli`, `wpa_passphrase`, systemd
units, D-Bus files, ifupdown hooks, examples, manuals and documentation. Detached
symbols retain non-executable modes. The package metadata describes the
installed payload and its actual source/ABI dependencies.

The same independent consumer executes `@sonic-wpa-supplicant//:package_test`
and `@sonic-wpa-supplicant//:upstream_test`. These cover payload bytes, modes,
links and timestamps; the three ELF/debug pairs; real dependency loading and
GDB source lookup; the IEEE PBKDF2 vector; and a private supplicant/control-client
PING/PONG exchange. Twelve native upstream programs build and nine
self-contained suites execute. Three HTTPS/X.509 programs have compile-only
coverage because their external fixtures are unavailable.

The source owner separately checks configured source counts, exact source and
configuration identities, and absence of WPA foreign-build or Debian-package
actions. Registry CI retains the existing AMD64 scope.

## Integration status

This is the first WPA registration on maintained registry `main`, preserving
the existing unpublished candidate version from the earlier review catalog.
Keep this registration Draft while source #1 is unlanded. Before marking it
Ready, refresh the archive to the maintained source integration commit and
rerun the same acquisition, independent-consumer and public-target checks.

[MACsec image #149](https://github.com/securely1g/sonic-buildimage/pull/149)
validates image assembly and the installed macsecmgrd/WPA handoff. Full VS
installer, physical MACsec traffic and ASIC/FIPS POST coverage remain separate
from this source-package registration.
