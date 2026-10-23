# AMD64 tools for ARM kernel cross compilation

`sonic-build-infra@0.0.19-161c46f2c52529239aeec345f272b583f5d7d4dd` supplies one AMD64 kernel
build runtime containing native tools, both ARM cross compilers, and their target
libraries. For example, `sonic-linux-kernel`'s ARM64 and ARMHF package actions use
the same runtime while selecting the AArch64 or hard-float ARM compiler. Target
libraries stay in separate Debian multiarch directories, and host generators use
AMD64 libraries. Native ARM64 builds retain their native runtime.

The source archive is pinned to `161c46f2c52529239aeec345f272b583f5d7d4dd`. The only source patch
sets the registry module version. Published versions remain unchanged.

Registry presubmits run on AMD64, build the shared runtime once, run a native
generator, cross-link both target programs with libelf and libcrypto, check ELF
machine/class, and verify declared Debian compiler and library dependencies.
The two target tests record the same runtime identity. Native AMD64 runtime
regressions also run here. Native ARM64 regression coverage belongs to source CI;
this registration does not claim an ARM64 host can cross-build ARMHF. Full kernel
packages and remote-cache reuse are validated in `sonic-linux-kernel` source CI.
