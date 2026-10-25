# DASH BMv2 source runtime and debug TARs

Register the landed source implementation from [DASH #1](https://github.com/securely1g/DASH/pull/1), commit `97c07d05193e346bc990e816e30a7e3d72e8f4c0`. The module runs the source-built P4 compiler and DASH generator, then wraps the upstream SAI metadata/library Make targets. It exports runtime/debug TARs and an installed SDK for [buildimage #13](https://github.com/securely1g/sonic-buildimage/pull/13), without a Debian package producer or legacy Make changes.

The source uses declared Make/M4/pkg-config/Aspell tools, preserved system-header classes, and explicit PI/gRPC/protobuf/Abseil link dependencies. Its PI, P4C, foreign-build adapter and shared infrastructure recipes are published on the maintained registry `main` branch. The registry applies only a module-version suffix patch; the source owns all build and runtime behavior.

Native AMD64 and ARM64 presubmits build `@sonic-dash//:runtime`, `:runtime.debug_symbols` and `:sdk`, then run `@sonic-dash//bazel:runtime_test`. They cover the installed SDK, generated pipeline files, an independent runtime loader, dependency closure, build IDs, debuglink checksums, DWARF and GDB source lookup. Both host and target use the declared Trixie toolchain.

The shared registry runner retains source, resolution, build/test and complete output-tree evidence. Full Syncd OCI integration and the later generated package metadata registration remain separate consumer work.
