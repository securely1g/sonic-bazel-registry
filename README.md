# SONiC Bazel registry

Each module version describes a complete source archive, its patches or overlays,
and their integrity hashes. Consumers pin a registry commit and choose module
versions from that snapshot. Publish changed build behavior under a new version;
changing an existing release in place would make its meaning depend on which
registry snapshot a consumer uses.

## SWSS dependency releases

### libnl3 3.7.0.sonic-buildimage.1

This release uses the same libnl 3.7.0 archive and SONiC RTA_NH_ID patch as
`3.7.0.sonic-buildimage`. The change is in `overlay/libnl3.BUILD`:
`linux_private_headers` no longer uses `strip_include_prefix`. That attribute
exported libnl's private Linux headers as transitive virtual include paths, so
SWSS consumers could pick those headers instead of the toolchain's kernel UAPI
headers. libnl itself still selects its private headers through the local
`LIBNL_COPTS` and Bison include flags.

The overlay is repeated because each registry version must be independently
fetchable; it is not a second libnl source fork. The unchanged RTA_NH_ID patch is
part of that complete overlay, not the reason for the new version.

### rules_distroless 0.9.4.sonic.1 and 0.9.4.sonic.2

These releases use the upstream **0.9.4 release archive**. They are not copies of
`0.0.0.commit-01bb79d7eef4eb3ce9511d3dfaf0ab386bd8d12d`, which fetches a different,
earlier source snapshot. Replacing the commit-named entry would misrepresent
its source and change an existing consumer's dependency graph.

`0.9.4.sonic.1` additionally declares `.inc` files under `usr/include/` as
headers in the Debian importer. Debian's protobuf development headers include
`google/protobuf/port_def.inc` and `port_undef.inc`; retaining only `.h` and
`.hpp` leaves those fragments out of the generated C++ target's declared inputs.
A sandboxed consumer of protobuf headers then cannot compile. The patch includes
only `.inc` files in the header tree, not arbitrary package data files.

`0.9.4.sonic.2` retains that fix and adds the Debian `armhf` to Bazel `arm`
platform mapping. Current SWSS and Common ARMHF consumers select this cumulative
release. The earlier releases remain unchanged.

### sonic-swss-common 0.0.0-99572f5a34e7f408dee49eaf2a3ba60c5d443fb6

This release fetches the merged Common source at
[`99572f5`](https://github.com/securely1g/sonic-swss-common/commit/99572f5a34e7f408dee49eaf2a3ba60c5d443fb6).
Common owns its Bazel build and migration history. The registry carries only a
patch to the module version, matching the source commit named by the release.

This replaces the draft `0.0.0-10d14ae58ae73899a52a2447d1e791a2b7bd1a34` entry,
which applied the entire Bazel migration to an older source archive. That draft
entry has been removed from the current index. Its already-published immutable
registry snapshots (including `ab3d2af909a4791bdc53d3aa48005c36cb7d528a` and
`3131031ad639e33a6a99599b954863f9e9f62532`) retain exactly their original contents
for historical consumers. SWSS advances both its Common version and registry
pin together; there is no in-place change to the old module's source or hashes.
