# Socat source packages for SONiC

This module compiles socat 1.8.0.2 from Debian's source package:
`socat_1.8.0.2.orig.tar.bz2` plus `socat_1.8.0.2-1.debian.tar.xz`.
Both archives are checksum-pinned to the values in `socat_1.8.0.2-1.dsc`.
The source repository applies `debian/patches/series` in order, directly from
the Debian archive. Debian's control files, build rules, copyright and patches
remain together; the registry does not keep copies of Debian-maintained patches
or copyright.

SONiC's [`enable_readline.patch`](https://github.com/securely1g/sonic-buildimage/blob/af35f605975215872e69dba5a291cb52fd5faafa/src/socat/patch/enable_readline.patch)
is retained separately and applied after Debian's series. Its file headers are
normalized for Bazel's patch reader; the changes to Debian files are unchanged. It adds
`libreadline-dev` to `debian/control` and removes `--disable-readline` from
`debian/rules`. The Bazel configure target also explicitly selects
`--enable-readline`; OpenSSL and TCP-wrapper support remain enabled.

The Bazel Central Registry has no socat module. This integration reuses the
upstream `rules_foreign_cc` configure/Make rule and SONiC's declared GCC,
Make and pkgconf tools. It builds the original source with its existing
configure script and Makefile. It does not run Debian packaging commands.
The Debian control files describe the original package; they do not cause a
DEB build or automatically resolve Bazel's dependency targets.

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
It also checks the fetched Debian copyright, readline build dependency and
Debian's rejection of overlong UNIX socket addresses.
It does not run upstream's unrestricted network/privileged test suite.

Target libraries come from the fixed Debian and Debian-security snapshots in
`sonic-build-infra`, with archive integrity checked by `rules_distroless`.
The resolver selects the same snapshot packages for both native architectures.
Build-time `-rpath-link` searches only the declared dependency directory; the
installed programs have no build-directory RPATH or RUNPATH.

When updating the source, update both source archive URLs and hashes from the
matching Debian `.dsc`, and check SONiC's readline patch still applies. The
Debian archive supplies the patch inventory; do not copy it into the registry.
Keep the required feature flags in the installed test;
configure can otherwise silently disable a feature when a library is missing.

## Generated runtime package metadata

`//:runtime_packages.json` is a generated target. The existing Debian
`control` and `changelog` define package fields; `BUILD.bazel` maps package names
to the existing Bazel TARs. The shared metadata rule inspects those target
binaries and declared dependency packages, so version constraints come from
the built artifacts and Debian tools. There is no handwritten JSON metadata
file or new DEB producer.
