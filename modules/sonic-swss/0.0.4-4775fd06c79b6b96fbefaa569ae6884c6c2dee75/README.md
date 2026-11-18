## Registry dependency refresh: `0.0.4-4775fd06c79b6b96fbefaa569ae6884c6c2dee75`

Source: `securely1g/sonic-swss@4775fd06c79b6b96fbefaa569ae6884c6c2dee75`, based on `9259312475d1f61598221d6f36d034089bcb5f55`. Dependency targets are frozen to published registry snapshot `3d1cc5e8dfd553d2acbe4198e504a245e6bdbddf`. The source owns the module base version and dependency updates. The registry supplies the full commit-qualified identity and retains its existing integration behavior.

Full archive patch-application and build validation must be recorded separately.

# SWSS with execution-platform SAI generation

This version registers SWSS master commit `9c3797990d4b5a79100a40fe7689927c18212361`. Both its Bazel dependency and its standalone archive override select Sairedis `0.0.5-33443ea1666a23812365d03fb959066ee84c9aa0`. An AMD64 runner can generate SAI sources with host Python while compiling the SWSS binaries for ARM64. [SWSS source change](https://github.com/securely1g/sonic-swss/pull/12)

The version retains the published SWSS 0.0.2 libteam providers, runtime and debug TAR exports, seven build targets and three tests on AMD64 and ARM64. Its one registry patch records the module version. When SWSS builds as the root module, Bazel uses its pinned Sairedis archive. When another project depends on SWSS, Bazel resolves the registered Sairedis module through that project's root configuration.
