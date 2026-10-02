# Kernel execution tools: 0.0.15-3a3d42932877e303385fd0b6503d1c413fc86bab

This entry publishes the declared Debian tool runtime required by
`sonic-linux-kernel`'s `//:kernel_packages` source build. The runtime contains
the pinned compiler, Make/Kbuild helpers, package tools and their dependencies.

The AMD64 registry consumer builds the complete `kernel_runtime` through a
small manifest-output target, then runs the rootfs preparation regression tests
and the actual chroot tool/packaging smoke test. The retained default output is
`kernel-runtime.json`; CI does not upload a second copy of the complete tool
tree. ARM64 kernel compilation, signed kernels and full image assembly are
outside this registration's validation scope.

The registered source is `3a3d42932877e303385fd0b6503d1c413fc86bab`. Source-repository CI remains separate
from registry consumer validation. Kernel compilation and remote-cache reuse
are exercised by the kernel source workflow and the downstream image consumer.
