# Generated Debian metadata for source-built images

Registers `0.0.22-878635ede0b4d79e52093b85d97810ac7fdcd97f` from the reviewed source commit.

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

It also includes the separate build-infra #64 cache fix. Internal tool-directory
aliases are materialized before caching, and relocated Debian tools prefer
canonical `/usr/lib` package paths when Bazel restores directory aliases as
ordinary directories. The kernel-runtime regression checks real dependency
lookup and package ownership; native source CI proves a fresh output directory
reuses the tool tree from disk cache and executes the test again.
