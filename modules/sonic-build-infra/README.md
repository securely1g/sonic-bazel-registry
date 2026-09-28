# sonic-build-infra registry validation

The presubmit manifests for `0.0.4-83b4e9d963f7f268d06983a8c954fc5d6d93ce2b.sonic.1`
and `0.0.7-91fe8246519f99838da936eee54e85208c704a4d` exercise the published module
as a dependency of a fresh consumer on native AMD64 and ARM64 Debian Trixie.

Both versions build and execute C++ consumers with the managed GCC toolchain,
with and without the `as_needed` feature. Analysis tests check the actual link
actions: host `/lib/...` paths must not be injected through `-rpath-link`, and
`--as-needed` must precede the linked dependency when enabled. The patched 0.0.4
version opts in; 0.0.7 enables the option by default and retains the explicit
feature without adding a duplicate flag.

The source-owned PIC, deployed-content, and debug-provider tests also run, and
the runtime and detached-symbol tar targets must both build. The 0.0.7 entry
additionally adapts the source-owned SWIG analysis tests to its external module
name: Python/Go bindings, 32/64-bit target widths, file/tree library inputs,
execution-tool configuration, transitive headers, and output groups are checked.
These are action-analysis tests; they do not claim ARMHF runtime execution.

The additional registry overlays contain only validation targets. Source
archives, release patches, and production build definitions retain their existing
bytes. The manifests name the selected checks explicitly; they do not run the
complete source test suite or the nested sysroot repository-assembly fixture.
