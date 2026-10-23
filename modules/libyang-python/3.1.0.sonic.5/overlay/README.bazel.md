# Build and package libyang-Python

The registry module `libyang-python` `3.1.0.sonic.5` builds the patched v3.1.0
CFFI binding from source for CPython 3.13. It consumes the registered source
target from `libyang` `3.12.2.sonic.4`.

Public outputs:

- `//:libyang`: Python library and CFFI extension for Bazel consumers.
- `//:libyang_pkg`: runtime TAR with Python modules, `py.typed`, stripped
  `_libyang.so`, the original license and `libyang-3.1.0.egg-info`.
- `//:libyang_pkg.debug_symbols`: matching native symbols under
  `/usr/lib/debug/.build-id`.

Declared Python, CFFI and setuptools execute the original `setup.py egg_info`
in an isolated source copy to generate installed distribution metadata.
The metadata action uses upstream's version override, declares all input files
and rejects unexpected output files. Its `genrule.tools` edge selects the
execution configuration. Metadata generation does not compile the CFFI
extension; the target-platform C/C++ toolchain compiles its generated C source.

With this module available through the SONiC registry, consumers select:

```sh
bazel build @libyang-python//:libyang_pkg @libyang-python//:libyang_pkg.debug_symbols
bazel test @libyang-python//:libyang_runtime_test \
  @libyang-python//:libyang_upstream_test \
  @libyang-python//:libyang_package_test
```

Use the dependency's configured repository alias if it differs. The registry
presubmit runs these outputs and tests on native AMD64 and ARM64 Debian Trixie
with Bazel 8.5.1 and CPython 3.13. Installed-package checks cover distribution
discovery and requirements, module bytes, import and schema behavior, native
library loading, debug build IDs, debug-link checksums and GDB source lookup.

The image must also supply CFFI and the native `@libyang//:libyang_pkg`.
The package test borrows declared CFFI runfiles while isolating the installed
binding and libyang library. These runtime/debug TARs do not install dependencies,
produce Debian packages or create dpkg package records.

## Generated runtime package metadata

`//:runtime_packages.json` is a generated target. The existing Debian
`control` and `changelog` define package fields; `BUILD.bazel` maps package names
to the existing Bazel TARs. The shared metadata rule inspects those target
binaries and declared dependency packages, so version constraints come from
the built artifacts and Debian tools. There is no handwritten JSON metadata
file or new DEB producer.
