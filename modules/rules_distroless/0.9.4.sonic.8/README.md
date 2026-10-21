# Quoted pkg-config arguments

This version retains every `0.9.4.sonic.7` fix and parses shell quotes and
backslash escapes in `.pc` flags after variable expansion. It also removes
quoting from the `includedir` and `libdir` values used to locate package files.
No shell substitutions or commands are executed.

Debian libpcap 1.10.5-2 has `prefix="/usr"` and
`includedir="${prefix}/include"`. The old whitespace splitter left nested
quotes in the generated include and linker paths, breaking the BMv2 foreign
build before compilation. These now resolve to `/usr/include` and the
architecture's `/usr/lib/<triplet>` directory. Quoted or escaped spaces inside
an argument remain intact; empty quoted arguments are omitted.

[Patch provenance and validation](PATCHES.md) documents the complete retained
patch set. The new parser regression covers real AMD64/ARM64 libpcap metadata,
single and double quotes, escaped spaces, literal quotes and backslashes.
The supported fixtures were compared with native pkg-config 1.8.1. An additional
native test compiles the actual pinned libpcap headers through their imported
compilation context. It omits runtime linker inputs and does not claim libpcap
runtime coverage. The shared registry CI runs all fourteen tests on native
AMD64 and ARM64; it downloads existing Debian inputs and creates no DEB packages.
