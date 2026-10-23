# Generated Debian metadata for source-built images

Registers `0.0.22-6dafd3595a75251748c1ca7502d5a8f6660e126b` from the reviewed source commit.

The source combines existing OCI account and installed-package helpers with
`runtime_packages`: package identity and dependency fields come from the owning
Debian control/changelog, while actual target ELF files determine shared-library
requirements. BUILD files retain package-to-TAR mappings. No new Debian packages
are produced. The generated metadata binds each record to its runtime TAR hash.

For example, Common's `libswsscommon` version `1.0.0` and
`//dist:libswsscommon_pkg` supply config-engine's installed package record without
maintaining another handwritten control record.

The registry retains published entries and the existing native AMD64/ARM64
compiler, runtime, stripping and debug checks. It adds the six OCI tests,
including real ELF dependency generation and execution/target library isolation,
and carries the published kernel-runtime checks. Registry wrappers execute the
original AMD64-to-ARM64/ARMHF cross-compiler tests on AMD64 and the native kernel
regression on ARM64. A test-only visibility patch permits this reuse; it changes
no compiler or runtime behavior.

This cumulative candidate also preserves build-infra #60's static C launcher
fix for GCC/Clang and its regression test.
