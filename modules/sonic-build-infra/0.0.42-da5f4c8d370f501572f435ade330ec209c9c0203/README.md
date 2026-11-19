# Shared build tools and direct debug-symbol packaging

Register merged Infra master `81476192bf2cdb70bb646e85935c5d698b6de8a0` as `0.0.39-81476192bf2cdb70bb646e85935c5d698b6de8a0`. It includes preserved link destinations during directory-alias materialization and direct final debug-symbol TAR creation from Infra PR #126.

Preserve the existing registry test overlay and public cross-test visibility patch. The presubmit retains the existing tool and package checks and includes the public debug-symbol manifest, ownership and mode tests.
