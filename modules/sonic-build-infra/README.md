# sonic-build-infra registry validation

The presubmit manifest for
`0.0.7-91fe8246519f99838da936eee54e85208c704a4d` exercises the module as a
dependency of a fresh consumer on native AMD64 and ARM64 Debian Trixie.

The release builds and executes C++ consumers with the managed GCC toolchain,
with and without the explicit `as_needed` feature. Analysis tests check the
actual link actions: host `/lib/...` paths must not be injected through
`-rpath-link`, and `--as-needed` must precede linked dependencies. The toolchain
enables the option by default and retains the explicit compatibility feature
without adding a duplicate flag.

The source-owned PIC, deployed-content, and debug-provider tests also run, and
the runtime and detached-symbol tar targets must both build. The entry adapts
the source-owned SWIG analysis tests to its external module name: Python/Go
bindings, 32/64-bit target widths, file/tree library inputs, execution-tool
configuration, transitive headers, and output groups are checked. These are
action-analysis tests; they do not claim ARMHF runtime execution.

Each architecture builds four explicit outputs and executes fifteen required
tests. The additional registry overlays contain only validation targets. Source
archives, release patches, and production build definitions retain their existing
bytes. These selected checks do not run the complete source test suite or the
nested sysroot repository-assembly fixture.
