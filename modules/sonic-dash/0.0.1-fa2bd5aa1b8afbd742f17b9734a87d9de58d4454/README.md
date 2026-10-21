# DASH runtime package metadata

Publishes `0.0.1-fa2bd5aa1b8afbd742f17b9734a87d9de58d4454` from [DASH #2](https://github.com/securely1g/DASH/pull/2) so Syncd can consume the producer's `//:runtime_packages.json` alongside its runtime TAR. The parent registration [#94](https://github.com/securely1g/sonic-bazel-registry/pull/94) supplies the source producer and dependency graph.

Runtime/debug build targets and existing native tests are preserved. This stacked metadata registration creates no DEB targets. It remains Draft while the source commit and parent registration are unmerged.
