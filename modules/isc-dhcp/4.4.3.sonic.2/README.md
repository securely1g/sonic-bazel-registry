# ISC DHCP 4.4.3-P1-2 relay

The registry uses normalized module version `4.4.3.sonic.1` for Debian source
`4.4.3-P1-2`. Its source archive is the original Debian packaging archive. The
unchanged Debian patch files and series are consumed directly as label inputs.
The native source repository downloads upstream only once, applies the ten
Debian patches in series order and the fourteen SONiC source patches from the
current Make series. SONiC patches 0005 and 0014 only change Debian build flags
and scheduling: their original files are preserved, `--enable-use-sockets` is
represented in the inspected configuration, and Bazel schedules compilation.
Patch 0106 is outside the current Make series and is excluded.

BIND 9.11.36 is extracted directly from the prepared upstream source's bundled
`bind/bind.tar.gz`. It is not independently downloaded or copied. Native C
libraries build the relay; configure is not invoked during ordinary builds.
AMD64 Trixie configuration substitutions were derived with the declared GCC
sysroot and APT zlib CcInfo using isolated `autoconf_probe` actions. The inspection
records live in the migration task's `components/isc-dhcp/probe` directory.
The profile follows Debian's final non-LDAP NSUPDATE pass, with sockets,
paranoia and process-ID logging enabled, and BIND threading, OpenSSL, GSSAPI,
LMDB, Python, JSON and XML disabled. Original per-file safe.c `-O0` is retained.

This module needs infra's `extract.archive_input` source preparation interface.
`dhcrelay` and `relay.runtime` are the public native binary and installation TAR
interfaces. Only the relay product required by the VS image is included.


The installation producer also retains the original relay init script, translated
man page, upstream README/RELNOTES, Debian changelog/NEWS selection and copyright.
Only final installed documentation is compressed, using the locked APT pigz.
Original Debian control helpers retain debconf templates/config and maintainer
scripts (including default configuration generation); they never execute those
scripts during the build.

Canonical public interfaces are `isc-dhcp-relay.runtime`,
`isc-dhcp-relay.runtime.debug_symbols`, `isc-dhcp-relay.runtime_metadata` and
`isc-dhcp-relay.control`. Existing `relay.runtime`,
`relay.runtime.debug_symbols`, `runtime_packages.json` and `dhcrelay` labels
remain available. No server/client product or enabled ATF test is introduced.
The installation test checks original resource bytes and modes, split debug
identity/DWARF, original package version and delivered Debian controls.

The updated recipe requires the source changelog helper and complete APT tools
from the pending infra release. Its temporary development CLI override is
validation evidence, not proof that the old declared infra release provides
these new interfaces. Formal version binding is finalized before publication.
