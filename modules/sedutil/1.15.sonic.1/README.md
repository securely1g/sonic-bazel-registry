# sedutil for SONiC AMD64

Preserve the official `1.15-5ad84d8` AMD64 release binary and the original SONiC Make installation at `/usr/local/bin/sedutil-cli` (0755, root-owned). The original product input is prebuilt; this entry does not compile or strip it.

- `:sedutil.runtime`: raw installation TAR.
- `:sedutil.runtime_metadata`: package identity, actual TAR digest, declared installed path and ELF runtime requirements through the shared producer interface.
- `:sedutil.control`: original finalized control in a raw TAR. Original Make has no dependency-calculation step; metadata retains the original fields without inventing Depends. Debian control tooling supplies its normal Section/Priority defaults.
- `:installation_test`: checks payload/control/metadata and runs an extracted installation copy's device-free `--help` through a declared APT target loader and libraries.

The release ZIP and the original Make recipe archive are fixed by checksum. No intermediate DEB or extra product compression is introduced. The prebuilt release supplies no new matching debug-symbol artifact.
