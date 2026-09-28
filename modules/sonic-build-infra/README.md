# sonic-build-infra registry validation

## Native release 0.0.6

`0.0.6-4fb4dca08ea10f7d60e9d217f476fd9a2f975ff2` registers the native AMD64/ARM64
toolchain and ELF packaging fixes without the later ARMHF sysroot and
32-bit SWIG APIs. It is the native prerequisite for the libyang-Python binding
and sonic-swss-common YANG migration.

The manifest creates an external consumer on native Debian Trixie AMD64 and
ARM64. It builds four explicit outputs: default and explicit `as_needed` C++
consumers, the deployed runtime tar, and its matching detached-symbol tar.
Twelve required tests cover consumer execution, link-action ordering and
absence of host `rpath-link` injection, PIC, deployed content, the debug
provider, explicit `as_needed` compatibility, and preservation of RPATH,
RUNPATH, and static ELF inputs through debug splitting.

The ELF preservation checks use the default `make_built_base=True` packaging
mode, which removes runtime search paths before splitting symbols. The source
PR separately exercises both packaging modes. Registry validation does not
claim the complete source test suite, ARMHF execution, or SONiC image boot.

The four registry overlay files contain validation targets only. The source
archive is pinned by commit and integrity; its sole registry patch aligns the
module version with the version directory. Historical entries keep their
original contents. The separate 0.0.7 registration remains deferred ARMHF work.

## Deferred shared-API release 0.0.7

This entry adds the shared sysroot and target-width SWIG APIs for the later
ARMHF integration. Common's native YANG migration selects the 0.0.6 entry above.
The published 0.0.7 archive, version patch, and validation inputs remain unchanged.

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
