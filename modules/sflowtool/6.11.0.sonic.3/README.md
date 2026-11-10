# sflowtool for the SONiC sFlow image

This entry builds the `sflowtool` executable selected by SONiC's
`src/sflow/sflowtool/Makefile`: upstream commit
`c953cfe8991286457080938a29fc72019f64718a`. Its `configure.ac` declares version
`6.11`; the registry represents that as `6.11.0.sonic.3` to follow the
three-component foreign-package version convention. The source revision has no
Bazel files and the Bazel Central Registry has no sflowtool module (checked
2026-11-10).

The consumer is `sonic-buildimage`'s `docker-sflow` family, tracked by
[producer issue #96](https://github.com/securely1g/sonic-buildimage/issues/96)
and [image issue #132](https://github.com/securely1g/sonic-buildimage/issues/132).
It installs `/usr/bin/sflowtool` to decode or forward sFlow datagrams. This
registration replaces the earlier `rules_foreign_cc` Autoconf/Make wrapper from
`6.11.0.sonic.2` with direct `rules_cc` targets; the Docker integration is
separate.

| Input or action | Before (`6.11.0.sonic.2`) | After (`6.11.0.sonic.3`) |
| --- | --- | --- |
| Build the pinned sflowtool source | Run `boot.sh`, `configure` and `make` via `rules_foreign_cc` with autoconf/m4/make execution toolchains | Compile `src/sflowtool.c` directly with `rules_cc` and a minimal generated `config.h` (`HAVE_BYTESWAP_H`, `VERSION`) |
| Supply `/usr/bin/sflowtool` to `docker-sflow` | Consume `@sflowtool//:runtime` | Unchanged (`@sflowtool//:runtime` and `@sflowtool//:runtime_packages.json`) |
| Inspect native symbols | `@sflowtool//:sflowtool` retains the unstripped binary via a debug transition | Single debug-compiled ELF feeds `:sflowtool`, `:runtime` and `:runtime.debug_symbols` with identical Build IDs |

No DEB is generated, no Make package cache or `rules_foreign_cc` toolchain is
required, and the legacy SONiC Make/Debian path is unchanged. Upstream
`src/Makefile.am` compiles a single C translation unit (`src/sflowtool.c` plus
four local headers), and `src/sflowtool.c` reads only `HAVE_BYTESWAP_H` and
`VERSION` from `config.h`. The only linked target dependency is libc from the
selected toolchain sysroot. Upstream has no test suite at this revision;
`package_test` exercises the installed artifact instead of inventing upstream
test coverage.

Public targets:

- `@sflowtool//:runtime`: `/usr/bin/sflowtool` (root, 0755) and the unchanged
  upstream `COPYING` notice at `/usr/share/doc/sflowtool/copyright`.
- `@sflowtool//:runtime_packages.json`: original package identity `sflowtool`
  version `6.11`, with the architecture and libc dependency derived from the
  actual runtime ELF; no DEB output.
- `@sflowtool//:runtime.debug_symbols`: symbols from the same deployed ELF.
- `@sflowtool//:sflowtool`: unstripped executable without build-tree RPATHs.
- `@sflowtool//:configuration`: generated `config.h` header.
- `@sflowtool//:package_test`: installed paths, metadata, architecture, libc-only
  linkage, RELRO/BIND_NOW hardening, build ID/debug-link/GDB checks including a
  negative control; sFlow v5 interface-counter decoding with IPv4 and IPv6 agent
  addresses; byte-for-byte forwarding to a private UDP collector;
  unsupported-version rejection.

Native AMD64 and ARM64 Trixie are the declared matrix. The registry's normal PR
CI builds all named outputs and runs the installed test from a fresh external
consumer. No full VS image, physical sampling or kernel psample behavior is
claimed.

The metadata target uses the unchanged `control` and `changelog` selected by
`sonic-buildimage` at `17807c19314b3397a694bd8070e3b515667b56b3`, under
`src/sflow/sflowtool/debian`. Its package version is `6.11`, independently of
the registry module version `6.11.0.sonic.3`. Recipe metadata is excluded from
compilation inputs, so a metadata-only edit does not rebuild the binary.
