# lldpd 1.0.16, native Bazel build

This entry retains SONiC's Debian source baseline `1.0.16-1+deb12u1`, its two
Debian patches, and its two SONiC patches. One registry portability patch
uses libbsd's public namespaced headers; see `PATCHES.md`. SHA256-verified original and Debian
archives are prepared by `sonic-build-infra`'s ordered source rule.

One native target graph supports AMD64 and ARM64 on Debian Trixie. Bazel owns
individual C compilation, target preprocessing, atom initializer generation,
shared-library linking, document templates, compression, and installation.
Autoconf is used only during migration to inspect the selected target toolchain.
Ordinary builds expand `config.h.in` directly and execute native language rules.

Public installation interfaces:

- `@lldpd//:lldpd.runtime`: daemon, CLI, `liblldpctl.so.4.9.1`, configuration,
  Debian init/systemd files, manuals, completions, documentation and copyright.
- `@lldpd//:lldpd.runtime.debug_symbols`: build-id-matched detached DWARF.
- `@lldpd//:liblldpctl-dev.runtime`: public headers, development symlink and
  pkg-config file.
- `@lldpd//:lldpd.runtime_metadata`: package identity and dependencies derived
  from the Debian recipe and actual installed payloads.
- `@lldpd//:lldpctl`: public headers and shared-library `CcInfo`.

The historical `:runtime` and `:runtime.debug_symbols` labels forward the
same artifacts and `DebugSymbolsInfo`. Consumers select this module version;
installation interfaces preserve the existing service and library layout.
The library directory follows the target platform's Debian multiarch triplet.
The original Libtool `13:1:9` ABI remains SONAME `liblldpctl.so.4`.

System dependencies consume public APT `CcInfo` from the shared production lock:
`frr_deps`, `dhcpmon_debian`, `iproute2_deps`, and `trixie`. These sets share
one fixed source configuration and one lock. Runtime test archives are separate
from compilation inputs. This entry introduces no component APT lock.

Debian PIE, SNMP, XML, readline, libbsd, protocol extensions and privilege
separation remain enabled. SONiC netlink receive buffers remain 2 MiB/4 MiB.
`lldpcli` retains UID 101, group `adm` GID 4 and mode 4750 to match the SONiC
parent image's `_lldpd` account. The image consumer creates that account,
implements service behavior, and handles the merged `/usr` service path.
A source TAR supplies installation content without executing maintainer scripts.

The nine unchanged upstream C suites validate protocol and parser behavior.
`package_test` checks the independent Debian installation inventory, public API
consumer, ELF architecture, PIE/RELRO/NOW, SONAME, installed loader resolution,
and matching build-id/debuglink/DWARF. Both architectures use the same checks;
execution checks require a native worker, while cross builds validate artifacts.
