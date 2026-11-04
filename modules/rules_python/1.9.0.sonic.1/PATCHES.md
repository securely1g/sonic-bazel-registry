# Patch provenance

Upstream: bazel-contrib/rules_python release 1.9.0, exact BCR archive and checksum.

- 0001-bcr-module-version.patch: unchanged BCR1.9.0 version alignment patch, sourced from https://bcr.bazel.build/modules/rules_python/1.9.0/patches/module_dot_bazel_version.patch .
- 0002-sonic-module-version.patch: local module identity alignment to1.9.0.sonic.1, no runtime behavior.
- 0003-preserve-wheel-metadata-and-modes.patch: local native py_wheel metadata attributes maintainer, maintainer_email, keywords and license_files; optional regular_file_mode threaded through existing wheelmaker action. Includes wheelmaker permission regression. Not submitted upstream.

License-File selects Core Metadata2.4 and caller supplies corresponding licenses/<path> files via existing extra_distinfo_files. Empty license_files retains2.1. regular_file_mode defaults empty for legacy0777;0644/0755 explicitly select ordinary file permission bits across source and generated wheel members.

Contracts: https://packaging.python.org/en/latest/specifications/core-metadata/ and https://peps.python.org/pep-0639/#license-files-in-project-formats . Preserve original License text; do not infer License-Expression.

Public registry consumer: @rules_python//registry_ci:metadata_test verifies three native wheels, changed/omitted fields, repeated License-File paths, regular ZIP modes and RECORD checksums. Source development validation also runs all upstream //tests/py_wheel/... and //tests/tools:wheelmaker_test.
