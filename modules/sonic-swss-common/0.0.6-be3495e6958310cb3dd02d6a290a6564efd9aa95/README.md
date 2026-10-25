# Common checks its runtime files before generating package metadata

Registers the source in [Common #32](https://github.com/securely1g/sonic-swss-common/pull/32)
at commit `be3495e6958310cb3dd02d6a290a6564efd9aa95`.
The ordinary `@sonic-swss-common//:runtime_packages.json` build now checks
required files inside the three runtime TARs before it records their hashes and
Debian package metadata. The checks travel with the producer instead of being
copied into every image.

[Buildimage #30](https://github.com/securely1g/sonic-buildimage/pull/30) consumes
these outputs for config-engine. For example, Common now owns the checks for
`usr/lib/{multiarch}/libswsscommon.so.0`, `libsonicdbcli.so.0` in that same directory,
`var/run/redis/sonic-db/database_config.json`, the Python binding and
`usr/bin/sonic-db-cli`. `{multiarch}` selects `x86_64-linux-gnu` on AMD64 and
`aarch64-linux-gnu` on ARM64. The metadata keeps the reviewed raw TAR paths;
image assembly handles any installed-path normalization.

| Input or action | Before | After |
| --- | --- | --- |
| Build Common metadata with its normal runtime TARs | Emits package controls and hashes; config-engine separately lists required Common files. | Checks Common files first and includes those requirements beside the controls and hashes. |
| Runtime TAR accidentally omits `libswsscommon.so.0` | An image owning that requirement detects the omission. | Common metadata generation fails before the image consumes it. |

This uses the shared producer check in [infra #66](https://github.com/securely1g/sonic-build-infra/pull/66),
registered by [registry #141](https://github.com/securely1g/sonic-bazel-registry/pull/141).
It changes neither compilation nor TAR layout, introduces no DEB producer, and
preserves all existing C++, Python, Go, Rust, runtime/debug and timestamp checks
on native AMD64 and ARM64. Existing published registrations remain unchanged.

The only registry patch, `0001-module-version.patch`, changes the source module
version `0.0.6` to the full registry version identifying this exact source commit.
