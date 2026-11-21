# Compressed debug sections by default

Register merged Infra master `54d22c948f9490c09ff0e1d9bdd25ad204f46672` as `0.0.40-54d22c948f9490c09ff0e1d9bdd25ad204f46672`. It includes Infra PR #123: `strip_binary` and `sonic_deploy_tar` now compress extracted DWARF by default, as Debhelper does for dbgsym packages. Set `compress_debug_sections = False` to keep uncompressed sections.

Preserve the existing registry test overlay, public cross-test visibility patch and presubmit from `0.0.39`.
