# sonic-sairedis runtime package metadata

Registers source `519a4748fdffb6534130bb1792b404021c6ca2c3` from [sonic-sairedis #5](https://github.com/securely1g/sonic-sairedis/pull/5). The public `@sonic-sairedis//:runtime_packages.json` describes the package identities and dependencies associated with its runtime TAR targets.

The source change adds metadata and documentation; native runtime/debug targets remain available. Registry CI retains the existing native AMD64/ARM64 producer tests and also requires the metadata export.

Consumers: [sonic-buildimage #30](https://github.com/securely1g/sonic-buildimage/pull/30) and [#13](https://github.com/securely1g/sonic-buildimage/pull/13) read the producer metadata instead of copying package fields into each image. The source commit is unmerged, so this registration remains Draft until it is refreshed to the landed source commit.
