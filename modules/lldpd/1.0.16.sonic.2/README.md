# LLDP source package for SONiC

The Bazel Central Registry has no `lldpd` module, and upstream `1.0.16` has no
Bazel definitions. This integration keeps the existing upstream build system.

This module keeps SONiC's `lldpd 1.0.16-1+deb12u1` baseline. It reconstructs
the Debian source from the two SHA256-verified source archives, applies Debian's
recorded quilt series, then applies the two SONiC patches in their maintained
order. The final hunk in SONiC's second patch has one missing context line;
only its hunk counts are corrected for Bazel's parser. All 470 prepared source
files were compared with GNU patch applying the unchanged legacy patch bytes.

The native AMD64/Trixie build uses upstream configure/Make through
`rules_foreign_cc`, the shared SONiC GCC/sysroot and shared execution tools.
The separate checked target-library lock contains the exact external Debian
headers/libraries used by this component. No component execution-tool set,
DEB producer, or Make package-cache dependency is introduced.

`@lldpd//:runtime` and `@lldpd//:runtime.debug_symbols` are the public installed
payloads. `lldpd`, `lldpcli` (also exposed through the `lldpctl` symlink), and
`liblldpctl.so.4.9.1` come from the same declared native source action. Detached
symbols are paired with the installed stripped ELFs. The source action retains
SONiC's 2 MiB/4 MiB netlink buffers and Debian's protocol, SNMP, XML, readline,
libbsd, PIE and privilege-separation selections.

The runtime payload includes upstream installed configuration/manual/completion
files plus Debian's defaults, init script and copyright. The numeric LLDP CLI
ownership follows the actual SONiC config-engine parent: `_lldpd` is UID101,
its primary group is GID102, and `adm` is GID4. `lldpcli` is UID101:GID4 mode4750.
The image consumer must declare the corresponding account using the existing
account-layer rule. A runtime TAR neither creates accounts nor executes Debian
maintainer scripts. Its installation and complete image behavior are separate
acceptance checks; this source module does not claim full LLDP image integration.

The nine unchanged upstream C protocol/parser suites run with declared target
libraries. Installed checks inspect exact payload bytes, ownership/modes,
symlinks, feature macros, ELF architecture/hardening, Build IDs and debug-link
checksums, and isolated GDB source-line/type lookup with a no-symbol negative
control. Only the exact built payloads are used for loader/version checks.
GDB is the same CI inspection tool already installed by registry validation.

Ordinary source changes are handled by upstream Make inside one Bazel foreign
action. Bazel caches that complete action and the separate TAR/image actions;
this module does not claim per-C-file Bazel compilation caching. Preserve the
checked source hashes, patch order and target-library lock when updating it.

The target lock selects AMD64 `check`, `libbsd-dev`, `libcap-dev`,
`libevent-dev`, `libpci-dev`, `libreadline-dev`, `libsnmp-dev`, and `libxml2-dev`
from the recorded Debian snapshots. Refresh it with the public
`rules_distroless` APT resolver when intentionally changing these inputs, and
keep one coherent version of each architecture/package in the imported lock.
For example, the selected security `linux-libc-dev` is `6.12.96-1`; retaining
both it and the older `6.12.86-1` from a separate root's resolution is invalid.
Execution tools continue to come from the shared `build_tools` set.

The installed service retains Debian's `lib/systemd/system/lldpd.service`
path. The OCI consumer must check how its parent's merged `/usr` filesystem
handles that path, along with the account and setuid ownership above.
