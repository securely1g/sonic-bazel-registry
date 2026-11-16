# SWSS with execution-platform SAI generation

This version registers SWSS master commit `9c3797990d4b5a79100a40fe7689927c18212361`. Both its Bazel dependency and its standalone archive override select Sairedis `0.0.5-33443ea1666a23812365d03fb959066ee84c9aa0`. An AMD64 runner can generate SAI sources with host Python while compiling the SWSS binaries for ARM64. [SWSS source change](https://github.com/securely1g/sonic-swss/pull/12)

The version retains the published SWSS 0.0.2 libteam providers, runtime and debug TAR exports, seven build targets and three tests on AMD64 and ARM64. Its one registry patch records the module version. When SWSS builds as the root module, Bazel uses its pinned Sairedis archive. When another project depends on SWSS, Bazel resolves the registered Sairedis module through that project's root configuration.
