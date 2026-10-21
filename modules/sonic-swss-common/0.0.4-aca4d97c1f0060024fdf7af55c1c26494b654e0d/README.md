# sonic-swss-common runtime package metadata

Registers source `aca4d97c1f0060024fdf7af55c1c26494b654e0d` from [sonic-swss-common #28](https://github.com/securely1g/sonic-swss-common/pull/28). The public `@sonic-swss-common//:runtime_packages.json` describes the package identities and dependencies associated with its runtime TAR targets.

The source change adds metadata and documentation; native runtime/debug targets remain available. Registry CI retains the existing native AMD64/ARM64 producer tests and also requires the metadata export.

Consumers: [sonic-buildimage #30](https://github.com/securely1g/sonic-buildimage/pull/30) and [#13](https://github.com/securely1g/sonic-buildimage/pull/13) read the producer metadata instead of copying package fields into each image. The source commit is unmerged, so this registration remains Draft until it is refreshed to the landed source commit.
