# sonic-build-infra 0.0.20-68832c2aad42470f4c983ead4279468529122b79

This source snapshot combines three reviewed changes:

- [infra #56](https://github.com/securely1g/sonic-build-infra/pull/56): avoid GCC environment limits when foreign builds have many include or library directories. For example, BMv2 can link `simple_switch_grpc` without overflowing the environment passed to `collect2`. Native library search order stays unchanged.
- [infra #57](https://github.com/securely1g/sonic-build-infra/pull/57): keep Debian's inherited users and groups when an image adds Redis or Syncd service accounts.
- [infra #58](https://github.com/securely1g/sonic-build-infra/pull/58): read source package versions and dependencies from their owners, and verify the installed runtime TARs against the selected modules and image receipts.

[Source commit](https://github.com/securely1g/sonic-build-infra/commit/68832c2aad42470f4c983ead4279468529122b79) is an integration snapshot, not a merged master commit. Keep its registration draft until the source changes land, then register the merged source revision and rerun native AMD64 and ARM64 CI.

The only registry patch sets the source module version to this commit-based registry version. No source implementation is patched here. Every existing registry version is preserved.

Presubmit retains the compiler/runtime build and test targets from registry #97 and adds five direct tests for account merging and installed-package metadata. Tests validate inherited account bytes, names/IDs, primary groups, whiteouts, OCI hashes, source owner identity and normalized ELF ownership/modes. No Debian packages are produced. Complete base/config-engine/Syncd image validation remains in the buildimage consumer PRs #30 and #13.

The public metadata rule uses `owner_metadata` because Bazel reserves `package_metadata`. Its action test supplies synthetic owner/module/TAR inputs and checks the generated status, source identity and actual payload hash.

The public-rule action test also exercises an aliased runtime TAR: the receipt keeps the source owner's public target label while hashing the actual payload.
