# Registry patches

- `0001-bump-version.patch`: align the source MODULE base `0.0.37` with this full maintained-commit version. It changes only the module version.
- `0002-registry-cross-test-visibility.patch`: retain the preceding entry's public visibility for the original native AMD64 cross-tool test executables and kernel runtime test. This permits the unchanged registry-owned consumer tests to depend on them.

The four registry-only overlay files preserve the external-prefix-map and kernel-tool consumer checks. Product implementations remain in the fixed source archive.
