# sonic-linux-kernel 0.0.4

This entry retains the fixed 6.12.41 kernel source archive and maintains its
Bazel adaptation in the registry overlay. It requires Infra 0.0.45.

All five Debian packages use native Bazel installation/metadata actions and
mtree payloads: runtime image, detached debug information, architecture headers,
common headers and kbuild tools. Seventeen packaged kbuild programs use native
C rules and explicit generators. Linux's own Kbuild compilation is retained.
The public runtime TAR, control archive, boot tree and metadata interfaces remain.

AMD64 Jenkins verification covered complete package contents, permissions,
links, control metadata, debug matching and external-module compilation.
The presubmit retains both AMD64 and ARM64 validation and adds the native
installation and tool-generator tests. Hosted results are recorded by CI.
