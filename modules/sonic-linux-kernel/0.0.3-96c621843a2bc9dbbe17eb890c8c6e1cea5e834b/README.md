# SONiC Linux 6.12.41

This Registry revision owns the Bazel implementation. Its fixed
sonic-linux-kernel archive supplies the Make recipe, configuration and SONiC
patches. Linux and Debian packaging archives use the Makefile's versions,
URLs and SHA256 values.

The shared prepared_source repository rule applies Debian's ordered quilt
series and the SONiC feature series once. Debian's base tree remains separate
from the SONiC feature tree, as required by the tools-header recipe. The compilation
action reads the SONiC source tree directly. Debian's generated setup target retains the Trixie
configuration merge and checks. One explicit Kbuild compiles the selected
image and modules with separately declared HOSTCC/host binutils and target
CC/CROSS_COMPILE. ARM64 on AMD64 uses the declared AArch64 and compatibility
compilers. Pahole uses one thread per Make job.

The runtime modules are installed once. Matching unstripped modules are moved
to the debug installation tree. Independent installation actions retain the maintained Debian package layouts
and export uncompressed installation TARs and controls. Final DEBs use the shared
sonic_deb rule. Runtime TAR, boot files, control TAR and metadata are available
without DEB compression, and kernel_module depends on compilation alone.
Debug packages contain matching symbols without a full Linux source copy. Generated headers, symbol versions and host helpers
form the compact external-module interface; the immutable prepared sources
are carried by KernelBuildInfo.

Public interfaces remain kernel_packages, linux-image.runtime,
linux-image.runtime_metadata, linux-image.control, boot, kernel_metadata.json
and kernel_build_outputs. kernel_module consumes the same Kbuild identity.
The action logs configuration, Kbuild, installation and export durations.
