# SONiC iproute2 source packages

This module builds Debian iproute2 **6.15.0-1** plus SONiC's bridge FDB protocol
patch with upstream configure/Make through `rules_foreign_cc`. The Bazel Central
Registry has no iproute2 module. Its installed files feed separate runtime and
matching debug TAR targets; no Debian package is produced.

## Source and build contract

`bazel/source.bzl` fetches the upstream and complete Debian source archives whose
SHA256 values are recorded in [the Debian source manifest](https://deb.debian.org/debian/pool/main/i/iproute2/iproute2_6.15.0-1.dsc).
It applies `debian/patches/series` in order, rejecting unsupported patch options,
then applies SONiC's bridge protocol patch. Debian's patches, copyright and
installation manifest remain owned by those source archives.

The declared SONiC GCC toolchain supplies the compiler, sysroot and linker.
Packaged Make, pkgconf, Bison and Flex run in the execution configuration.
Pkgconf reads the declared target libraries' metadata, with host search paths
disabled. The small `bazel/configure.sh` adapter preserves these tools and flags
because upstream resets `CC`/`LEX`, defaults Berkeley DB headers to `/usr/include`,
and runs feature probes without normal compiler flags. It runs the unchanged
upstream configure script; upstream Makefiles own source selection and parser
and netem generation.

The recipe retains Debian's `hardening=+all` policy, including stack-clash,
format, fortify and architecture-specific branch protection, with `-O2`, `-g`,
linker hardening, automatic color output, `/run/netns`, multiarch library paths
and declared feature libraries. Make installs into a private `DESTDIR`; packaging uses those staged
programs, configuration, generated manuals, completions and netem tables.
Examples and notices come directly from the source, as in Debian's recipe.

Native AMD64 and ARM64 builds are supported. Upstream's netem generators use
`HOSTCC` and execute during Make, so these jobs do not establish cross-compilation
support. Bazel caches the configure/Make action as a whole. Data and config
selections use the same debug-preserving configuration as the ELF inputs,
avoiding a second configured foreign build. Runtime/debug TAR
assembly and consuming image assembly remain separate cacheable actions.

## Public targets

- `@iproute2//:iproute2_pkg`: Debian's 15 installed native programs, `routel`,
  configuration, netem tables, headers, completions, manuals, examples and notices.
- `@iproute2//:iproute2_pkg.debug_symbols`: detached symbols from those same linked
  programs under `/usr/lib/debug/.build-id`.
- `@iproute2//:iproute2_config`: upstream configure's actual `config.mk`.
- `@iproute2//:iproute2_package_test`: installed-program, feature and debug checks.

The TAR uses merged-`/usr` paths and preserves the `ctstat`, `rtstat` and
`/usr/sbin/ip` links. Debian's manifest excludes `ifstat`, so its built binary
and manual are not packaged. Manuals are uncompressed. The TAR supplies files;
it does not run Debian maintainer scripts, grant capabilities or create dpkg
records.

## Validation and maintenance

After auditing the selected action graph for DEB-producing actions, run on a
native host with the matching SONiC platform:

```sh
bazel build --platforms=@sonic-build-infra//platforms:x86_64_trixie \
  @iproute2//:iproute2_pkg @iproute2//:iproute2_pkg.debug_symbols \
  @iproute2//:iproute2_config
bazel test --platforms=@sonic-build-infra//platforms:x86_64_trixie \
  @iproute2//:iproute2_package_test
```

The package test uses the shared Python toolchain so it reuses the same
configured TARs built for upload.

The test compares all 15 programs with `debian/iproute2.install`; checks required
features, dynamic handlers, generated parsers, `ip moo`, bridge FDB protocol
support, a read-only `lo` query and private runtime library loading; and checks
build IDs, debuglink CRCs and GDB source locations for every program. A test-only
preload adapter redirects `tc`'s fixed ematch-map paths to the extracted package.
Debian skips upstream's root-requiring tests because they leave network state
behind; the package tests are unprivileged.

For an upgrade, update both source archives and hashes from the new `.dsc`,
the source prefix and module version. Review Debian's dependencies, rules,
patch series and installation manifest, then validate both native architectures.
Ordinary C source changes are picked up by the declared source tree and upstream
Makefiles; no per-file Bazel source map needs to be maintained.

## Generated runtime package metadata

`//:runtime_packages.json` is a generated target. The existing Debian
`control` and `changelog` define package fields; `BUILD.bazel` maps package names
to the existing Bazel TARs. The shared metadata rule inspects those target
binaries and declared dependency packages, so version constraints come from
the built artifacts and Debian tools. There is no handwritten JSON metadata
file or new DEB producer.
