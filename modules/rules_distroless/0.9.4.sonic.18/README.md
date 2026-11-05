# Distributed APT requests and workspace locks

Components keep their `apt.install` and `apt.install_file` declarations. A root
`apt.import_lock` selects the production graph for the shared extension;
dependency locks remain standalone defaults. Sources still use `sources_file`.

`apt.export_requests(name = "apt_request_export")` creates the public
`@apt_request_export//:requests` JSON export without fetching package indexes.
It contains evaluated requests, the selected source document, production lock
path and root `apt.lock_view` outputs. Collection-only repositories provide the
existing `use_repo` namespaces without fetching DEBs.

`apt.lock_view(file = "//image:apt.lock.json", dependency_sets = ["image_deps"])`
declares an updater-managed compatibility view, not a second production graph.
Production locks with `_inputs.distributed = true` require exact agreement with
the current evaluated request document, including removals.

Use the sonic-build-infra workspace updater to collect, resolve and publish.
Original DEB/data/control targets, library exports and versioned repositories
remain available. Existing package identities and checksums remain enforced.

Optional source-record `default_architectures` selects the nonempty subset of
`architectures` used for requests without architecture qualifiers. Explicit
qualifiers can still select other configured architectures. Omitting the field
preserves the previous all-configured-architectures behavior. Infrastructure
uses AMD64/ARM64 defaults while retaining explicit ARMHF cross inputs.

## Native library contracts

APT library imports preserve installed-file ownership and GNU linker-script
semantics through native shared-library boundaries. A script may refer to a
shared object, static archive, object file or nested script. GROUP and AS_NEEDED
remain linker-controlled. Runtime exports contain ELF libraries using their
SONAMEs; text scripts remain link inputs. Ambiguous runtime SONAMEs fail during
analysis instead of silently choosing a library. Multiple pkg-config libraries
resolve independently, including libraries supplied by dependency packages.

Run the original cross-package script regression from the registry root:

```sh
USE_BAZEL_VERSION=8.5.1 python3 \
  modules/rules_distroless/0.9.4.sonic.18/tests/shared_linker_script_test.py \
  --registry .
```

The complete contract fixture uses the production sonic-build-infra CcInfo
adapter supplied by the caller. It builds six two-level shared-library chains,
checks AS_NEEDED and constructor behavior, rejects conflicting SONAMEs, and runs
both Bazel and installed executables without LD_LIBRARY_PATH or LD_PRELOAD.
The build directory is hidden during installed execution. Optional Go CGo and
Rust executables consume the adapter's actual CcInfo flags and files.

```sh
USE_BAZEL_VERSION=8.5.1 python3 \
  modules/rules_distroless/0.9.4.sonic.18/tests/library_contract_test.py \
  --registry . --adapter /path/to/sonic-build-infra/cc/shared_library.bzl \
  --go /path/to/go --rustc /path/to/rustc
```

For an ARM64 execution check on an AMD64 host, supply `--cross-info compiler.json`
and `--qemu /path/to/qemu-aarch64-static` instead of the language options. The
JSON contains `cc` (absolute aarch64-linux-gnu-gcc path), `sysroot` (absolute
root), and `flags` (compiler argument array for that sysroot). The fixture uses
these files in a declared Bazel cross toolchain, verifies AArch64 ELF headers,
and executes the resulting programs through QEMU with the supplied sysroot.

Requires Python 3, Bazel 8.5.1, gcc, ar, dpkg-deb, xz and readelf. All packages
and locks are synthetic; the tests fetch no production package index and build
no business component. Each run prints its retained evidence directory.
