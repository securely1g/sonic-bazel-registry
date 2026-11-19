# Single-pass debug-symbol archives and cached tool runtimes

Register merged source [81476192](https://github.com/securely1g/sonic-build-infra/commit/81476192bf2cdb70bb646e85935c5d698b6de8a0), including [Infra #126](https://github.com/securely1g/sonic-build-infra/pull/126).

Component debug archives and OCI debug layers now map original symbol files
through an installation mtree into one uncompressed final tar. This removes the
collected symbol directory and intermediate archive while preserving installed
paths, payloads, metadata and symlinks. The manifest regression joins the existing
archive ownership, mode, timestamp and runtime/debug pairing tests.

The source also retains [Infra #124](https://github.com/securely1g/sonic-build-infra/pull/124)'s cached tool runtime and locked PMON package input fixes. Existing package versions, hashes, dependencies and inherited overlays remain unchanged. The registry patches align the module version and inherited cross-test visibility. Published registrations remain unchanged.
