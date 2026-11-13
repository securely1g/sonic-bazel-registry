# SOCAT 1.8.0.2 for SONiC

This module builds SOCAT, filan and procan with native Bazel C rules. It retains
Debian source version `1.8.0.2-1`, the Debian patch series and SONiC's readline
patch, plus the network namespace termination fix from `1.8.0.2.sonic.6`.
The ordered source preparation uses the shared `prepared_source` rule.
No configure or Make invocation participates in the production action graph.

The upstream `config.h.in` is expanded using values established with the pinned
GCC 14.2.0, Debian Trixie sysroot and declared library interfaces. The fixed
configuration enables readline, OpenSSL and TCP wrappers. Target platform
selection preserves the AMD64 and ARM64 ABI differences. Upstream tests retain
the SONiC `nocheck` selection.

Public outputs:

* `:built_socat1`, `:built_filan`, `:built_procan`: native program targets.
* `:socat_pkg`: stripped installation TAR, including the original Debian
  documentation, examples, compressed manuals and links. Changelogs retain
  their full source history; compression uses the shared source-built gzip
  toolchain.
* `:socat_pkg.debug_symbols`: matching build-ID debug information.
* `:runtime_packages.json`: package identity, computed runtime dependencies and
  the installation TAR digest, derived from the Debian metadata.
* `:socat_package_test`: installed layout, metadata and actual program behavior
  using the declared target loader and library payloads, including detached
  debug-symbol matching and debugger source-line lookup.

Use Bazel 8.5.1. The standalone root pins the compatible rules_cc API; another
root must retain that same override. Register the module's dependencies from
the maintained SONiC registry and BCR. The module's `.bazelrc` selects the
Trixie target platform and imports optional local configuration.

```sh
bazel build //:socat_pkg //:socat_pkg.debug_symbols //:runtime_packages.json
bazel test //:socat_package_test
bazel build --platforms=@sonic_build_infra//platforms:aarch64_trixie \
  //:socat_pkg //:socat_pkg.debug_symbols //:runtime_packages.json
```

The current validation uses AMD64 execution and ARM64 cross-compilation. ARM64
execution requires a matching native environment. Final DEB packaging, Make
integration and complete container-image assembly are separate consumers.
