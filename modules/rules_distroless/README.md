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
