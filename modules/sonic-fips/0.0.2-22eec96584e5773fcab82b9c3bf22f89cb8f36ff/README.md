# sonic-fips runtime package metadata

Registers source `22eec96584e5773fcab82b9c3bf22f89cb8f36ff` from [sonic-fips #6](https://github.com/securely1g/sonic-fips/pull/6). The public `@sonic-fips//:runtime_packages.json` describes the package identities and dependencies associated with its runtime TAR targets.

The source change adds metadata and documentation; native runtime/debug targets remain available. Registry CI retains the existing native AMD64/ARM64 producer tests and also requires the metadata export.

Consumers: [sonic-buildimage #30](https://github.com/securely1g/sonic-buildimage/pull/30) and [#13](https://github.com/securely1g/sonic-buildimage/pull/13) read the producer metadata instead of copying package fields into each image. The source commit is unmerged, so this registration remains Draft until it is refreshed to the landed source commit.
