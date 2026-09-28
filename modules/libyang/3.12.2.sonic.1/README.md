# libyang 3.12.2.sonic.1

This module builds the libyang source used by SONiC rather than importing the
Debian `libyang3` binary package. `source.json` verifies the Debian upstream
source archive and each overlay/patch file independently.

The native patch is the byte-identical
[`0001-pr2362-lyd_validate_noextdeps.patch`](https://github.com/securely1g/sonic-buildimage/blob/9ab452d22773c41783092ae3bd6c206d6c257c8d/src/libyang3/patch/0001-pr2362-lyd_validate_noextdeps.patch)
from the production buildimage input. `_FILE_OFFSET_BITS=64` matches its Make
recipe. The explicit source list follows all library and built-in type/plugin
sources in libyang's `CMakeLists.txt`, plus `compat/compat.c`. Public headers are
flattened as CMake installs them, including `plugins_exts/metadata.h`.

The overlay supplies the glibc feature configuration for little-endian SONiC
Linux targets. Plugin directories use the selected target's Debian multiarch
path. The x86_64, aarch64, and armv7 layouts are declared; a layout does not by
itself establish execution or toolchain support. Common's CI exercises native
AMD64 and ARM64. ARMHF and cross execution remain unvalidated for this release.

PCRE2 10.45 and xxHash 0.8.3 come from the Bazel Central Registry and are compiled
from source as static implementation dependencies. This differs from the Debian
binary package's shared PCRE2/xxHash dependency tree. Their archive symbols are
hidden from libyang's dynamic API. PCRE2 headers remain visible to consumers
because libyang's public structures refer to PCRE2 types; the static PCRE2 archive
is not propagated to consumers. The main library keeps SONAME `libyang.so.3` and
libyang project/ABI versions `3.12.2` / `3.9.1`.

Public targets:

- `@libyang//:libyang`: C/C++ shared-library dependency and public headers.
- `@libyang//:libyang.so.3`: linked shared library.
- `@libyang//:libyang_pkg`: runtime tar with `libyang.so.3.9.1` and relative
  `.so.3` / `.so` symlinks under `/usr/lib/<multiarch>`.
- `@libyang//:libyang_pkg.debug_symbols`: matching detached symbols, produced
  from the same debug-enabled ELF by SONiC's `sonic_deploy_tar` rule.
- `@libyang//:libyang_test`: dynamic consumer that parses a YANG module and data,
  exercises PCRE2 pattern validation, and uses `LYD_VALIDATE_NOEXTDEPS`.
- `@libyang//:libyang_package_test`: checks the archive's SONAME, symlinks, runtime
  dependencies, detached build ID/debuglink checksum, and GDB source-line lookup.
  Requires the same host `binutils`, `gdb`, and Python tools as Common's package
  tests.

The library's built-in modules remain embedded in the compiled sources. This
release supplies runtime tar archives; Debian metadata, a development-package
archive, standalone `yanglint`/`yangre` tools, and separately packaged libyang
models/plugins are outside this module's current target set.

The integration consumer is
[sonic-swss-common#6](https://github.com/securely1g/sonic-swss-common/pull/6).
Its schema generator resolves libyang in the execution configuration; target
libraries and runtime packages resolve it in the target configuration. Enabled
CI builds, tests, and retains the source-built runtime and matching symbols;
disabled CI omits YANG from swsscommon.
