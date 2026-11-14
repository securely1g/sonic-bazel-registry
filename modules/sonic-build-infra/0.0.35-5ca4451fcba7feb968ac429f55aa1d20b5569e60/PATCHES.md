# Patch provenance

- `0001-bump-version.patch`: align the original `0.0.35` MODULE from
  `securely1g/sonic-build-infra@5ca4451fcba7feb968ac429f55aa1d20b5569e60` with this registry snapshot.
  Origin: https://github.com/securely1g/sonic-build-infra/commit/5ca4451fcba7feb968ac429f55aa1d20b5569e60.
  Upstream status: registry-only identity alignment; no upstream implementation
  change is proposed by this patch. The HOME fixes are already in that source.
- `0002-registry-cross-test-visibility.patch` and all four `registry_ci` overlay
  files: inherited byte for byte from published `0.0.35-4016babb62e9eb97a71398b4d77ec9cfa5c62062`.
  Their existing native AMD64 wrapper checks and visibility purpose are unchanged.
