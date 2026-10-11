# Source-owned YANG model distribution

This entry selects the standalone module under `src/sonic-yang-models` in
[sonic-buildimage #32](https://github.com/securely1g/sonic-buildimage/pull/32).
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
