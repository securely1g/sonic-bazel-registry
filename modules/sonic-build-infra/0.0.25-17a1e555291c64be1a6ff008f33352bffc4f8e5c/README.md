# Optional paths in checked source receipts

This version registers [build-infra #69](https://github.com/securely1g/sonic-build-infra/pull/69) for [buildimage #13](https://github.com/securely1g/sonic-buildimage/pull/13). Syncd's `:installed_packages` target consumes source package receipts whose producer metadata may omit optional path requirements. The `libnl-3-dev` header TAR has such metadata: the previous guard rejected it before generating the installed-package records.

The selected source permits an empty path requirement only with a validated source receipt. Contract, base image, APT receipt, module identities, nonempty inventory, native-byte coverage and raw TAR hash checks remain active. Declared required paths must still be present, and legacy inputs without a source receipt retain their path requirement.

The published .24 entry remains unchanged. Both numbered patches and validation overlays are retained; only the version patch identifies this landed source commit. The unchanged native AMD64 and ARM64 presubmits select all 32 build targets and 27 test targets, including the expanded `oci/tests:installed_packages_test` regression cases and installation-link tests.
