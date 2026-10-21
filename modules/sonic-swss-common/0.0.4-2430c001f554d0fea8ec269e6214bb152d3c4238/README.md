# sonic-swss-common runtime package metadata

Registers source `2430c001f554d0fea8ec269e6214bb152d3c4238` from [sonic-swss-common #28](https://github.com/securely1g/sonic-swss-common/pull/28). The public `@sonic-swss-common//:runtime_packages.json` describes the package identities and dependencies associated with its runtime TAR targets.

The source change adds metadata and documentation; native runtime/debug targets remain available. Registry CI retains the existing native AMD64/ARM64 producer tests and also requires the metadata export.

Consumers: [sonic-buildimage #30](https://github.com/securely1g/sonic-buildimage/pull/30) and [#13](https://github.com/securely1g/sonic-buildimage/pull/13) read the producer metadata instead of copying package fields into each image. The source revision is the landed `master` commit. This registration remains Draft while its registry CI prerequisites are unmerged.
