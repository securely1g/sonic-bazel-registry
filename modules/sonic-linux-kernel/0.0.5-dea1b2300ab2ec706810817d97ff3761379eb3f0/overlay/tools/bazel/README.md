# SONiC kernel Bazel interfaces

The Registry module builds Linux 6.12.94 with the maintained Debian configuration
and SONiC patches. Execution tools come from the locked `sonic-build-infra`
runtime. AMD64 native builds and AMD64 to ARM64 cross builds use the host platform
for tools and the target platform for kernel code.

The build has separate Kbuild, installation and Debian assembly actions. Selecting
raw files or building an external module runs Kbuild without Debian installation
or compression. Selecting image assembly inputs installs the runtime package
without producing any DEB. Final DEBs use the shared `sonic_deb` rule and consume explicit mtree mappings
directly. The public runtime TAR is produced lazily from the same mapping.

| Public target | Contents and consumers |
| --- | --- |
| `//:image`, `//:vmlinux`, `//:System.map` | Direct Kbuild files |
| `//:config`, `//:Module.symvers`, `//:kernel.release` | Matching configuration and module ABI |
| `//:kernel_build_outputs` | Compact generated headers and host helpers for external modules |
| `//:linux-image.runtime` | Uncompressed installation TAR for rootfs and initramfs |
| `//:linux-image.control` | Debian control information and maintainer scripts |
| `//:linux-image.runtime_metadata` | Source package metadata with `RuntimePackagesInfo` |
| `//:boot` | `boot/vmlinuz-*`, `config-*`, `System.map-*` for ONIE |
| `//:kernel_metadata.json` | Architecture, release, module directory and boot SHA256 |
| `//:runtime_deb` | Runtime DEB |
| `//:debug_deb` | Matching vmlinux/module symbols and GNU build-ID links |
| `//:development_debs` | Configured headers, common headers and kbuild tools |
| `//:manifest` | Schema4 identity, provenance, hashes and sizes of all five DEBs |
| `//:kernel_packages` | All five DEBs and manifest; `kernel_artifacts` remains an alias |

Package basenames remain `<package>_6.12.94-1_<architecture>.deb`; common headers
use `all`. Each shared `sonic_deb` output is a directory containing that single
DEB. The Make and CI exporters consume these directories directly and publish
the original basenames.

Linux source files remain read-only inputs. Bazel configuration and installation
actions read the maintained Debian configuration/template APIs directly. They
execute neither `debian/rules.gen` nor `dh_*` packaging commands. Kbuild uses an independent `O=` directory; large final files
and module trees move from it to declared outputs. Debug packages contain symbols,
not a duplicate Linux source tree. Runtime modules retain signing and stripping;
debug modules remain unsigned with their original debug information. The Debian recipe remains the source for package fields, hooks, layouts and the
runtime System.map notice; Bazel declares their generation and mtree mappings.
The 17 kbuild executables use native C/C++ rules and explicit source generators.
Dynamic library dependencies are computed by the declared `dpkg-shlibdeps` tool.
Large debug files are archived from compiler outputs without a copied package
tree or intermediate payload TAR rewrites.
The `//:System.map` target exports the real map.

```sh
bazel build --platforms=@sonic_build_infra//platforms:x86_64_trixie //:kernel_packages
bazel build --host_platform=@sonic_build_infra//platforms:x86_64_trixie \
  --platforms=@sonic_build_infra//platforms:aarch64_trixie //:linux-image.runtime //:boot
```

External module consumers use the same compiled kernel:

```starlark
load("@sonic_linux_kernel//tools/bazel:kernel.bzl", "kernel_module")

kernel_module(
    name = "driver",
    kernel = "@sonic_linux_kernel//:kernel_packages",
    makefile = "Makefile",
    srcs = glob(["*.c", "*.h"]),
)
```

`deps` passes symbol versions from other `kernel_module` targets built against the
same kernel. `make_vars` supplies module-specific variables. Outputs include the
module directory, `Module.symvers`, and `modules.order`. Linux 6.12 uses `M=` as
both module source and output directory, so module actions keep private writable
module inputs and generated build data; they reference the prepared Linux source
directly.

The public `//tools/bazel:kernel_config` JSON string setting retains the existing
Make configuration mapping. This producer currently supports VS, Trixie, the
pinned kernel version and an unsigned boot image. Compilation concurrency follows
the available CPU affinity. The shared build cache configuration is unchanged.

Normal and kdump initramfs remain image assembly outputs. Configuration-dependent
`depmod` and target-system installation configuration remain with their consumers.
