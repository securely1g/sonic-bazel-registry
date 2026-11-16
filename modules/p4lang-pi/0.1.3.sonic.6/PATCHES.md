# Adaptation inputs

- `patches/0001-native-build-metadata.patch` removes the source archive's legacy Bazel package boundaries so one explicit native declaration can own the original Automake products. The fixed orig archive has zero `optional ` occurrences in P4Info, so the original Debian `sed` is an identity transform for this input. This patch only changes build metadata and the existing Debian source-preparation transform.
- `overlay/bazel/0002-use-boost-1.83.patch`, `0003-remove-protobuf-from-debian-dependency.patch`, `0004-remove-init-file.patch` preserve the original bytes and order from sonic-buildimage `1f6f381b793859e8db058cd813893bd0ee484b48`, `src/p4lang/p4lang-pi.patch/`. They apply only to the fixed Debian metadata archive.
- `overlay/bazel/sdk_test.cc` retains the existing registry SDK consumer. Other overlay files are the native Bazel implementation.

- `patches/0005-remove-unused-nested-bazel-packages.patch` removes the remaining
  vendored P4Runtime example and googletest test package boundaries. Those
  BUILD files refer to the original upstream workspace rather than this native
  producer. The patch changes build metadata only and follows patch 0001.
