# Native SONiC build interfaces

Registers merged [Infra #132](https://github.com/securely1g/sonic-build-infra/pull/132), commit `45b500f6e821df5ebe981abdbb82797ed3abd4fd`, with source module base version `0.0.42`.

The source supplies immutable APT inputs, runtime package metadata helpers, configured installation paths, DTrace and Python PGO tools. Existing AMD64 and ARM64 presubmits are retained. Both architectures add the configured installation path test; AMD64 additionally builds the two new execution tools.
