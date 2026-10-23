# Sairedis metadata from its Debian recipe

Registers [sairedis #6](https://github.com/securely1g/sonic-sairedis/pull/6), source `6e0119fdc2d1fa3a17626987856ef8ae156548fb`. The public `@sonic-sairedis//:runtime_packages.json` is now generated from the existing Debian control/changelog and the four actual runtime TARs, using the shared generator registered by [registry #120](https://github.com/securely1g/sonic-bazel-registry/pull/120).

For [syncd-vs in buildimage #13](https://github.com/securely1g/sonic-buildimage/pull/13), `syncd-vs` remains mapped to `@sonic_sairedis//syncd:syncd_pkg`. Its version and control fields come from the original recipe. That recipe places its shared-library substitutions in `Recommends`; generation preserves this placement instead of promoting them to `Depends`. The JSON also binds each record to its actual runtime TAR digest. No runtime compilation, TAR layout, or legacy Debian recipe changes.

Dependencies are generated from Common's actual package trees via [registry #104](https://github.com/securely1g/sonic-bazel-registry/pull/104). DASH-enabled image consumers also pass `--@sonic_sairedis//:dash_runtime_metadata=@sonic_dash//:runtime_packages.json` alongside the existing DASH SDK setting. The default registry job retains all native producer tests and builds all four metadata records; the DASH variant is validated with its image consumer.

This is a new `0.0.2` registration. Published `0.0.1` inputs remain unchanged. CI retains the native AMD64/ARM64 runtime/debug targets and seven producer test targets, and builds the generated metadata output.
