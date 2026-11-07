# SWSS with execution-platform SAI generation

SWSS 0.0.3 selects Sairedis 0.0.5 so SAI stub generation uses execution-platform Python when AMD64 builds ARM64 outputs. It also uses the SWSS 0.0.2 libteam source providers. The registered version appends the source revision to the version declared by SWSS. [SWSS source](https://github.com/securely1g/sonic-swss/commit/42df8c74af53427be97609a7b11e9aec59d2d454) · [Sairedis registration](https://github.com/securely1g/sonic-bazel-registry/pull/253)

The presubmit declares seven build labels and three tests for AMD64 and ARM64, including the libteam runtime and debug exports. The identity patch applies to the version field in the archived MODULE.bazel.
