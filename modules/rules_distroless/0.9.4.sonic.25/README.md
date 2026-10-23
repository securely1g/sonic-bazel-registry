# Include roots for declared headers

This version retains the complete `0.9.4.sonic.9` patch set and stops adding
`<package>/usr/include` to `CcInfo` when a Debian dependency owns no declared
headers or additional compiler inputs. Headerless runtime libraries still
propagate their linker inputs and transitive dependency contexts unchanged.

The BMv2 foreign build exposed 81 such nonexistent include roots. They enlarged
GCC's collected option environment without providing any headers. This change
removes those roots; a separate compiler adapter change addresses the remaining
argument-size limit with long build paths.

Four analysis regressions cover headerless, direct-header, additional-input
and transitive-header contexts, including linker flag order. Native AMD64 and
ARM64 CI retains the sixteen existing import, pkg-config, shared-library and
Boost CMake/Make tests. No DEBs are produced.

See [patch provenance and validation](PATCHES.md).
