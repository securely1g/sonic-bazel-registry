# Cached tool runtimes and PMON inputs

Register [the ordinary source merge aa060652712c3b729355b84362d028c892068e9c](https://github.com/securely1g/sonic-build-infra/commit/aa060652712c3b729355b84362d028c892068e9c) from [sonic-build-infra #124](https://github.com/securely1g/sonic-build-infra/pull/124).

The kernel tool producer publishes real directories while preserving file-link destinations and the existing handling of optional files. This lets metadata consumers restore the declared tool tree through their normal cache configuration. The PMON collection now selects its already locked libsensors-config package without changing existing package versions, hashes or dependency records.

Keep the established AMD64/ARM64 consumer matrix, archive contract tests and overlays from the published 0.0.38 registration. The registry patch changes only the module version and inherited cross-test visibility. All published entries remain unchanged.
