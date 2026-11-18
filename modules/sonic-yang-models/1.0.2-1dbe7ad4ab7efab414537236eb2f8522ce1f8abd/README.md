## Registry dependency refresh: `1.0.2-1dbe7ad4ab7efab414537236eb2f8522ce1f8abd`

Source: `securely1g/sonic-buildimage@1dbe7ad4ab7efab414537236eb2f8522ce1f8abd`, based on `c7cbc6d71b284f94fde0e47bb71aa308684ecbdf`. Dependency targets are frozen to published registry snapshot `3d1cc5e8dfd553d2acbe4198e504a245e6bdbddf`. The source owns the module base version and dependency updates. The registry supplies the full commit-qualified identity and retains its existing integration behavior.

Full archive patch-application and build validation must be recorded separately.

# Source-owned YANG model distribution

This entry selects the standalone module under `src/sonic-yang-models` from landed
[sonic-buildimage #32](https://github.com/securely1g/sonic-buildimage/pull/32),
at maintained `master` commit `b0a9362a7a1b4b5e1b7188c019d256f7c8aaff9f`.
The only registry patch aligns the module version with the immutable source SHA.

`yang_models_wheel` builds the existing setup.py distribution from source.
`yang_models_pkg` installs its Python metadata and both model variants using
the shared wheel-layer rule. `yang_models` keeps the prepared Python model tree.

The source container base in
[buildimage #30](https://github.com/securely1g/sonic-buildimage/pull/30), consumed
by [buildimage #13](https://github.com/securely1g/sonic-buildimage/pull/13), needs
the installed metadata so pip recognizes config-engine's sonic-yang-models
requirement. Native AMD64 and ARM64 registry CI checks the source wheel,
installed distribution discovery, complete manifests, file bytes and ownership.
It builds wheel and TAR outputs and creates no Debian packages.
