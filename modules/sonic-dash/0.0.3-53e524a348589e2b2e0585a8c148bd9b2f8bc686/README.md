# DASH recursive Make compiler flags

Register [DASH #4](https://github.com/securely1g/DASH/pull/4) at `53e524a348589e2b2e0585a8c148bd9b2f8bc686` as the separate `0.0.3` candidate. Both published versions remain unchanged. The source owns the response-file adapter and regression; the registry applies only the module version patch.

[Gearbox buildimage #154](https://github.com/securely1g/sonic-buildimage/pull/154) reaches DASH's original recursive Make call with 86,193 bytes of compiler flags and 64,724 bytes of linker flags. GNU Make combines those overrides into a 151,870-byte environment value, so Linux rejects a child before its compiler starts. The source launcher keeps the complete ordered `CPPFLAGS` value in a standard GCC driver response file, expanded at its original argument position. Compiler and linker lists remain separate in the original recipes.

| Input or action | Published `0.0.2` | This candidate |
| --- | --- | --- |
| Recursive Make with the retained Gearbox flag sizes | Environment export exceeds Linux's per-string limit | Make exports a short response-file reference |
| Include roots and macro overrides across both compiler variables | Original order is required | Driver response preserves that order; a preprocessor-only response is a tested negative control |
| Runtime/debug/SDK/package metadata | Existing source-owned public outputs | Same targets and installed contract |

The ordinary consumer explicitly selects published Distroless `.16` and the accepted infrastructure `.26-2cfc059` from [registry #209](https://github.com/securely1g/sonic-bazel-registry/pull/209), available through this PR's complete review base. This selects the actual native interface used by the image without changing the source owner's declared minimum. The review base preserves maintained registry main `d33cf63059703c5f981532b4357d416b8352db1d` and imports the exact infrastructure entry; this PR adds one DASH feature commit above it.

Presubmits retain all four public outputs, the original installed runtime/SDK/pipeline/GDB test and both native architectures, then add the real recursive-Make compiler regression. Source validation has passed that regression on native GCC14 and through Bazel. The complete retained compiler argument vector produces identical backend arguments and an 89,108-byte GCC options export with the driver response. Full ordinary package and installed wide-consumer acceptance remain pending; neither a catalog nor this source regression establishes completed Gearbox acceptance. No DEB producer is added or selected.

The source archive declares `archive_type = tar.gz` because the pinned codeload URL ends in the source revision. The source revision differs from the originally tested `5fb62ec` only by one README spelling correction; the full source archive file/mode comparison preserves every other input.
