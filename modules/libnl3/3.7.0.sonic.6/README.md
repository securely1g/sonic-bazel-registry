# Source-built libnl packages

The `3.7.0.sonic.6` candidate retains the libnl 3.7.0 source archive and SONiC
nexthop patch, and uses native Trixie AMD64/ARM64 source compilation. It does not
produce DEBs. Existing released registry entries remain unchanged.

## Updating module dependencies

Edit this version's `MODULE.bazel`. It is the single maintained module
definition. From the registry root, regenerate the copy installed into the
upstream source archive and its `source.json` checksum:

```sh
python3 ci/registry_ci.py sync-module --module libnl3 --version 3.7.0.sonic.6
```

`overlay/MODULE.bazel` is generated; do not edit it manually. The registry reads
the maintained file for dependency resolution. Source checkouts and local
module overrides use the generated copy. Registry CI checks that the copy and
checksum are current before building the module. To run that check locally:

```sh
python3 ci/registry_ci.py sync-module --module libnl3 --version 3.7.0.sonic.6 --check
```

## Image package boundaries

Use these public TAR targets when recording individual installed packages:

| Target | Installed files |
| --- | --- |
| `libnl-3-runtime_files` | Versioned core DSO, SONAME link, `/etc/libnl-3/{classid,pktloc}` |
| `libnl-route-3-runtime_files` | Versioned route DSO and SONAME link |
| `libnl-genl-3-runtime_files` | Versioned generic-netlink DSO and SONAME link |
| `libnl-nf-3-runtime_files` | Versioned netfilter DSO and SONAME link |
| `libnl-cli-3-runtime_files` | Versioned CLI DSO, SONAME link and ten CLI plugins |
| `libnl-3-dev_files` | Public headers, core static archive, unversioned core link and core pkg-config file |
| `libnl-route-3-dev_files` | Route static archive, unversioned route link and route pkg-config file |

Every `*-runtime_files` target also exposes `.debug_symbols` and the shared debug
provider for OCI image assembly. The runtime and development files do not overlap.
Libraries use `/usr/lib/<multiarch>`; this canonicalizes Debian's core `/lib`
placement for SONiC's merged `/usr` filesystem. Public headers are regular `0644`
files. Both runtime configuration data and the compiled `SYSCONFDIR` use
`/etc/libnl-3`, following Debian's `etc-libnl-3` patch.

The package split follows the `libnl-3-dev.install`, `libnl-route-3-dev.install`
and runtime manifests in
[Debian 3.7.0-0.2 packaging](https://deb.debian.org/debian/pool/main/libn/libnl3/libnl3_3.7.0-0.2.debian.tar.xz)
(SHA256 `35ae5b6ee3a56abd3ae8603fd47c3e38c9302d02a2d498fb88a3e2f2791ac2f0`).
The existing `*_pkg` and `*_dev_pkg` targets remain aggregate compatibility APIs;
they include development symlinks or additional runtime/header/pkg-config files
and should not be recorded as the precise individual Debian package inventories.

## Static archives and validation

Standard `cc_static_library` creates both static archives from the existing
compiled objects. The route archive selects the route and two generated parser
targets' own linker inputs, excluding the separately shipped core archive. The
small `archive_inputs.bzl` rule only forwards providers; it runs no archive tool
or compiler and leaves existing C/C++ targets unchanged.

Native presubmits build all legacy and precise TARs. The development-file test
checks disjoint package inventories, ownership, modes, configuration lookup,
shared linking and static linking. Its static consumer includes every archive
member to catch missing parser objects and duplicate core objects. Existing
consumer and package tests continue to check all five DSOs, ten plugins, matching
debug symbols and GDB source lookup. No host libnl DSO is accepted as the tested
package's runtime dependency.

## Generated runtime package metadata

`//:runtime_packages.json` is a generated target. The existing Debian
`control` and `changelog` define package fields; `BUILD.bazel` maps package names
to the existing Bazel TARs. The shared metadata rule inspects those target
binaries and declared dependency packages, so version constraints come from
the built artifacts and Debian tools. There is no handwritten JSON metadata
file or new DEB producer.
