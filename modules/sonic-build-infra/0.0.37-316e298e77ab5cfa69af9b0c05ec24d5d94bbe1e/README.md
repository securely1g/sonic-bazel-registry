# sonic-build-infra 0.0.18-95cd3a9050551247063ef31eea4a48269dc50866

Publish the relocatable native AMD64 and ARM64 kernel build tools from
[infra #62](https://github.com/securely1g/sonic-build-infra/pull/62). The
`sonic-linux-kernel` package target and [buildimage #6](https://github.com/securely1g/sonic-buildimage/pull/6)
use these declared compilers, interpreters and Debian packaging tools to build
under Bazel's Linux sandbox without root, chroot or a kernel worker container.
ARM64 retains the native ARM32 compiler and linker for its compatibility vDSO.

[Source revision](https://github.com/securely1g/sonic-build-infra/commit/95cd3a9050551247063ef31eea4a48269dc50866).
This revision is the landed squash of infra #62. Its source tree is identical
to the previously validated PR head; the version patch is the only source
patch. This replaces the superseded unmerged candidate while preserving every
version already on registry main.

Presubmit builds the runtime provenance manifest and requires native AMD64 and
ARM64 checks for rootfs metadata, Debian helper relocation, Python/Perl data,
compiler execution, package dependency lookup, transitive runtime loading and
shared-library layout. The runtime check moves the tool tree, compiles and runs
C/C++ host programs, and checks deployment executables do not retain its private
loader/RPATH. ARM64 also compiles and links an ARM32 compatibility-vDSO probe.
The runtime check also builds and inspects a small Debian package using the
declared packaging helpers and libmagic database. Full kernel builds and
fresh-output cache-hit verification remain in the kernel source and buildimage CI.
