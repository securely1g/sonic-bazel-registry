# Socat source packages for SONiC

This module compiles socat 1.8.0.2 with the seven patches from Debian's
`socat_1.8.0.2-1.debian.tar.xz`. Each patch records its source and purpose.
SONiC's `enable_readline.patch` changes Debian packaging to enable readline;
the Bazel configure target expresses that choice directly with
`--enable-readline`. OpenSSL and TCP-wrapper support also remain enabled.

The Bazel Central Registry has no socat module. This integration reuses the
upstream `rules_foreign_cc` configure/Make rule and SONiC's declared GCC,
Make and pkgconf tools. It builds the original source with its existing
configure script and Makefile. It does not run Debian packaging commands.

## Public targets

- `@socat//:socat_pkg`: stripped programs `socat1`, `filan`, `procan`, the
  `socat` symlink, upstream helper scripts, manuals and copyright files.
- `@socat//:socat_pkg.debug_symbols`: matching detached symbols under
  `/usr/lib/debug/.build-id`.
- `@socat//:socat_package_test`: installed-program and debug-symbol checks.

The programs use `/usr` paths. Installation is staged inside the Bazel action;
no file is installed on the build host. The manuals remain plain `.1` files,
which the man command supports, instead of Debian packaging's gzip copies.

## Build and validation

Use native AMD64 or ARM64 with the corresponding SONiC Trixie platform:

```sh
bazel build --platforms=@sonic-build-infra//platforms:x86_64_trixie \
  @socat//:socat_pkg @socat//:socat_pkg.debug_symbols
bazel test --platforms=@sonic-build-infra//platforms:x86_64_trixie \
  @socat//:socat_package_test
```

The parent workspace must select this module and `sonic-build-infra`. Registry
CI uses a separate consumer workspace and runs both architectures natively.
The test needs `binutils` and GDB, which the registry CI environment installs.
It checks all three programs with a private extracted library set, OpenSSL,
readline and TCP-wrapper feature flags, a stdin/stdout transfer, installed
scripts/manuals, ELF build IDs, debuglink checksums, and GDB source locations.
It does not run upstream's unrestricted network/privileged test suite.

Target libraries come from the fixed Debian and Debian-security snapshots in
`sonic-build-infra`, with archive integrity checked by `rules_distroless`.
The resolver selects the same snapshot packages for both native architectures.
Build-time `-rpath-link` searches only the declared dependency directory; the
installed programs have no build-directory RPATH or RUNPATH.

When updating the source, update the original archive hash and Debian patch
provenance together. Keep the required feature flags in the installed test;
configure can otherwise silently disable a feature when a library is missing.
