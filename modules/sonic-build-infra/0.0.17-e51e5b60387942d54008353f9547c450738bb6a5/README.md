# Build shared libraries without copying and importing them again

This candidate registers `sonic-build-infra@0.0.17-e51e5b60387942d54008353f9547c450738bb6a5`.
SWSS Common uses its adapter to expose a native `cc_shared_library` to C++,
Go and Rust consumers without copying the output or wrapping it in `cc_import`.
The adapter preserves the library's linking information and runtime files.

The source uses the pinned Debian GCC toolchains and keeps their RUNPATH
behavior. It does not include the global RPATH flag proposed in build-infra #50.
For example, the regression executable loads a middle library, and that library
loads a leaf library through its own runtime search path.

Native AMD64 and ARM64 registry tests run this indirect-dependency example and
inspect the executable and libraries for their runtime names, dependencies, and
RUNPATH tags. Existing compiler, build-tool, shared-library, runtime-TAR and
debug-symbol checks remain selected. These selections do not build DEB packages.

The source commit is on `codex/native-shared-library` and has not merged. This
registration is a preview for Common's native validation; it does not replace
registry #80 or change existing published entries. Native CI results are pending.
