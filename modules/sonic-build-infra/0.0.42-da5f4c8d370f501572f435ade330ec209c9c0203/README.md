# SONiC build infrastructure release

Register source base version `0.0.37` at the maintained commit [`d31541a95fdf477302f1b109f2105eee81c86617`](https://github.com/securely1g/sonic-build-infra/commit/d31541a95fdf477302f1b109f2105eee81c86617). This includes the source, OCI control, Python installation, Rust release and locked APT tool interfaces needed by the VS image migration, including declared BSDtar execution inputs and original Debian changelog projection.

The changelog API delegates filename and history selection to the locked Debian helper, then lets consumers apply their final pigz compression. Its source implementation landed in [infra #118](https://github.com/securely1g/sonic-build-infra/pull/118), following [the BSDtar tool closure in #117](https://github.com/securely1g/sonic-build-infra/pull/117). The dependency requests published SDK21; the presubmit consumer selects that same SDK.

The entry preserves the preceding release's build/test targets, native AMD64/ARM64 platforms and AMD64 cross-tool checks. It adds the source-owned OCI control, Python runtime, APT image-tool, linker operand, BSDtar and changelog regressions for the new interfaces. See `presubmit.json` for the exact targets. Native and installed producer validation is recorded separately from downstream full VS acceptance.
