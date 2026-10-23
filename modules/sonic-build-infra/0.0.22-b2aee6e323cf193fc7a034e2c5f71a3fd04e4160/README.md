# Generated Debian metadata for source-built images

Registers `0.0.22-b2aee6e323cf193fc7a034e2c5f71a3fd04e4160` from the landed build-infra #58 squash commit.

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
and carries the published kernel-runtime checks. Standalone registry wrappers
execute the original AMD64-to-ARM64/ARMHF cross-compiler tests on AMD64 and
the native kernel-runtime regression on ARM64. A test-only visibility patch
allows these wrappers to reuse the existing source tests; no build-tool behavior
is changed.
