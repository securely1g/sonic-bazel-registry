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

## Shared-library linker-script regression

Patch 0023 keeps runtime files, cross-package linker-script inputs and search
paths on the library-bearing CcInfo linker input. This preserves them when
rules_cc filters metadata-only inputs while building a cc_shared_library.

The standalone regression constructs two tiny DEBs, imports a development
package whose GNU linker script refers to the runtime package, and links a
shared-library consumer in a sandbox. It verifies the runtime SONAME in
DT_NEEDED and executes the consumer, requiring the known result 43. It uses
no production APT index or business component. Run from the registry root:

```sh
USE_BAZEL_VERSION=8.5.1 python3 \
  modules/rules_distroless/0.9.4.sonic.18/tests/shared_linker_script_test.py \
  --registry .
```

Requires gcc, dpkg-deb, xz, readelf and Python 3 on the native platform. Evidence
is retained in the printed temporary directory.
