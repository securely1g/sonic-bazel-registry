# DASH recursive Make compiler and linker flags

Register [DASH #4](https://github.com/securely1g/DASH/pull/4) at `1c56e8a12e91ec69add6fa98caccced92d216005` as `0.0.3-1c56e8a12e91ec69add6fa98caccced92d216005`. The source owns the flag adapter and regression tests. Published DASH `.1` and `.2` entries remain unchanged; the registry patch only sets the module version and removes root-only review overrides.

For example, the [full VS build for buildimage #133](https://github.com/securely1g/sonic-buildimage/actions/runs/42457158787/job/128659011067) could not start DASH's declared Make executable: `Argument list too long` stopped `docker-syncd-vs.gz`. The new source runs its flag adapter before that first Make invocation, then reuses the shared infrastructure helpers inside the original recursive compile and link recipes.

The separate registry reproducer retains 492 library search arguments in a 130,698-byte `LDFLAGS` value. The earlier compiler-only response file still lets GNU Make expand `MAKEFLAGS` to 131,872 bytes. Simply putting linker arguments into another GCC response file also fails: GCC expands them again in `COLLECT_GCC_OPTIONS`. The shared helpers preserve the ordered arguments in a private file and shorten absolute `-L` paths relative to the actual compiler working directory before launching GCC.

| Before | After |
| --- | --- |
| Recursive Make exports compiler and linker lists that exceed Linux's per-string limit. | The initial adapter stores the lists before launching Make, and recursive commands carry short references. |
| A plain linker response file still overflows GCC's child-process environment. | The shared configure environment helper shortens library search paths without dropping or reordering them. |
| Metadata linking, compilation and library linking use different flag sets. | Those original phases and flag positions are preserved; compiler flags are not inserted into linker-only recipes. |
| Consumers use DASH's runtime TAR, debug TAR, SDK and generated package metadata. | The same public targets and installed contract remain available; no DEB producer is introduced. |

This extends the original compiler-response fix for [Gearbox buildimage #154](https://github.com/securely1g/sonic-buildimage/pull/154), preserving its source commits and regression. Its prior [registry #209](https://github.com/securely1g/sonic-bazel-registry/pull/209) and [registry #218](https://github.com/securely1g/sonic-bazel-registry/pull/218) dependency receipts describe historical inputs, not acceptance of this updated graph.

The current graph selects infrastructure `0.0.28-8e15b3341e4665f7bf6ed9be0aaaf1c92dcf9175`, PI `0.1.3.sonic.3`, P4C `1.2.4.2.sonic.3`, Distroless `0.9.4.sonic.18` and TAR `0.10.5.sonic.2`. The source-owned root overrides allow standalone review; the registry removes those includes and resolves the complete candidate recipes normally. [PATCHES.md](PATCHES.md) describes the registry-only patch.

Local validation of the unchanged production files passes the real GNU Make/GCC14 argument-vector regression, the normal Bazel `//bazel:make_flags_test`, and analysis of the actual DASH Make action. The analysis confirms both public helpers and their declared Python runtime are inputs and that the adapter runs before Make. These are flag-transport and action-wiring results, not a completed SDK or VS build.

Normal registry CI retains four public build targets and both tests (`runtime_test` and `make_flags_test`) on native AMD64 and ARM64, including the installed runtime/SDK/pipeline/GDB checks. Full package builds and image acceptance remain required on this exact source and dependency graph.
