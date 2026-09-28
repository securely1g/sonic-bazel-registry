# Native sonic-build-infra registry validation

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
