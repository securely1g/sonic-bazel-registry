## Dependency refresh for `5.34.3.sonic.2`

This candidate retains the `5.34.3.sonic.1` source and existing patches. Its module dependencies select the newest non-yanked versions published at `3d1cc5e8dfd553d2acbe4198e504a245e6bdbddf`. Versions introduced by this refresh are not dependency targets of the same refresh.

# Monit 5.34.3 SONiC native module

Build the Debian 1:5.34.3-1 source with its four Debian patches and the original
SONiC alert-repeat patch using native C, Bison and Flex actions. Configuration
headers preserve the controlled AMD64 GCC14.2/Trixie probe. No configure or
Make wrapper runs in the normal build.

Public installation targets are monit.runtime, monit.runtime.debug_symbols,
monit.runtime_metadata and monit.control. original_check_binaries builds all
15 original noinst programs; the original Make check does not execute verify.
The installation test runs only --version and -t on isolated configuration,
and verifies installed permissions, controls, deployment ELF, compressed
DWARF and original changelog/NEWS behavior. It does not start a daemon.

Canonical source-package controls project the real generated control tree.
The original Debian changelog helper emits raw installed documentation, then
pigz performs final gzip compression. Empty trimmed NEWS is omitted. Runtime
TARs stay uncompressed; the installed executable test extracts only its ELF
with the declared APT BSDtar tool.

The development dependency sonic-build-infra0.0.37 requires the frozen local
API combination until an actual full-SHA release provides controls and
changelog interfaces. Formal no-override consumption is a release prerequisite.
