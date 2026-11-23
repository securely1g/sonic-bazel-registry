# Native Bash 5.2.37

Builds the existing Debian 5.2.37-2 and SONiC plugin sources with native C/C++ rules on Linux AMD64 and ARM64. The original source archives and patch order remain fixed.

The platform selects the declared Trixie compiler, shared locked development libraries, hardening flags and installed bashbug machine identity. Runtime TAR, detached symbols and package metadata retain the existing public labels: `bash.runtime`, `bash.runtime.debug_symbols`, `bash.runtime_metadata`, `bash.control` and `bash.runtime_receipt`.

Presubmit builds these interfaces on both architectures and checks installation content, ELF identity, symbols and metadata without running target programs. AMD64 additionally executes the original SONiC plugin and shell CLI checks.
