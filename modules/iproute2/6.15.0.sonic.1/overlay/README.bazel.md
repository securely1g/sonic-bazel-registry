# SONiC iproute2 source packages

This module builds iproute2 6.15.0 from Debian's complete 6.15.0-1 source
package, then applies SONiC's bridge FDB protocol patch. The Bazel Central
Registry has no iproute2 module. The build reuses upstream
`rules_foreign_cc.configure_make`, the original configure/Make files, and
SONiC's declared compiler, Make, Bison, Flex and pkgconf tools.

## Debian source assembly

`bazel/source.bzl` assembles the two archives identified by
[Debian's source manifest](https://deb.debian.org/debian/pool/main/i/iproute2/iproute2_6.15.0-1.dsc):

1. Extract `iproute2_6.15.0.orig.tar.xz` (upstream source).
2. Extract `iproute2_6.15.0-1.debian.tar.xz` (the complete `debian/` directory).
3. Apply every patch in `debian/patches/series`, in that order.
4. Apply SONiC's bridge FDB protocol patch.

Both archive SHA256 values are pinned in `MODULE.bazel` and match the `.dsc`.
Bazel's native downloader, extractor and patch implementation perform this
preparation; no host `dget`, quilt or Debian package build is involved. The
registry's single-archive source entry also fetches the upstream archive;
Bazel's repository download cache lets the preparation reuse those bytes.

Packaging reads `debian/copyright` directly. The installed-program test reads
`debian/iproute2.install` directly, so a changed Debian program list fails the
test until the Bazel layout is updated. Neither file nor Debian's patches are
copied into the registry overlay. To upgrade, update the two archive identities
from the new `.dsc`, the source directory prefix in `bazel/source.bzl`, and the
module version; review Debian's patch series and rerun both native CI jobs.

The module preserves Debian's source and patch inputs. Compilation still uses
upstream configure/Make, and TAR assembly uses `bazel/iproute2.BUILD.bazel`;
it does not execute `debian/rules` or claim identical Debian packaging behavior.

## Public targets

- `@iproute2//:iproute2_pkg`: all 15 native programs selected by Debian's
  `iproute2.install`, `routel`, configuration files, netem distributions,
  headers, completion files, manuals, examples and copyright files.
- `@iproute2//:iproute2_pkg.debug_symbols`: matching detached symbols under
  `/usr/lib/debug/.build-id` for all 15 programs.
- `@iproute2//:iproute2_package_test`: installed-program, feature and debug checks.
- `@iproute2//:iproute2_config`: the generated configure receipt.

Paths use the base image's merged `/usr` layout. For example, `ip` is stored at
`/usr/bin/ip`; the base's `/bin` symlink keeps `/bin/ip` working. `ctstat`,
`rtstat` and `/usr/sbin/ip` retain their links. The conflicting `ifstat` program
and manual are excluded, matching Debian's package manifest. Manuals are plain
`.3`, `.7` or `.8` files instead of Debian packaging's gzip copies.

No Debian package is produced and no file is installed on the build host.
The package does not grant network administration capabilities. Debian's
optional `iproute2/setcaps` setting defaults to false as well.

## Original configure and Make integration

IpRoute2 has its own configure script. `bazel/configure.sh` prepares a private
directory of symlinks to the original Debian `.pc` files, which describe each
library's version, headers and link options. It invokes the declared pkgconf
program with those files and relocates only its path variables to the existing
staged dependencies. The metadata contents remain unchanged.

The script also records the selected compiler, parser generators and flags in
`config.mk` for recursive Make. It keeps dependency include flags after
iproute2's own include flags, so its newer Linux headers retain precedence.
The normal configure probes require xtables, libbpf, ELF, libmnl, Berkeley DB,
SELinux, libtirpc and libcap support. Trixie libc provides `strlcpy`;
the original configure script uses libbsd only when libc lacks that function. The installed test fails when a
required feature is silently disabled.

## Validation

Use a native AMD64 or ARM64 host and the matching SONiC Trixie platform:

```sh
bazel build --platforms=@sonic-build-infra//platforms:x86_64_trixie \
  @iproute2//:iproute2_pkg @iproute2//:iproute2_pkg.debug_symbols
bazel test --platforms=@sonic-build-infra//platforms:x86_64_trixie \
  @iproute2//:iproute2_package_test
```

The test compares the packaged native programs with the unchanged Debian
manifest. It verifies Debian's `ip moo` patch, source configuration files, the SONiC `bridge fdb`
protocol option, the `ip`/`tc`/`ss` versions, a read-only netlink query of `lo`,
root ownership, declared private runtime libraries, and all ELF/debug pairs
with build IDs, debuglink checksums and GDB source locations. Registry CI
provides Python, binutils and GDB for this validation.

Debian's own build skips the upstream test suite because it needs root and
leaves network state behind. This target follows that policy and adds the
unprivileged installed-package checks above.
