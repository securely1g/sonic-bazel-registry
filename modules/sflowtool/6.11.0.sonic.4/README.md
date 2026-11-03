# sflowtool for the SONiC sFlow image

This entry builds the `sflowtool` executable selected by SONiC's
`src/sflow/sflowtool/Makefile`: upstream commit
`c953cfe8991286457080938a29fc72019f64718a`. Its `configure.ac` declares version
`6.11`; the registry represents that as `6.11.0.sonic.1` to follow the
three-component foreign-package version convention. The source revision has no
Bazel files and the Bazel Central Registry has no sflowtool module (checked
2026-11-03).

The consumer is `sonic-buildimage`'s `docker-sflow` family, tracked by
[producer issue #96](https://github.com/securely1g/sonic-buildimage/issues/96)
and [image issue #132](https://github.com/securely1g/sonic-buildimage/issues/132).
It installs `/usr/bin/sflowtool` to decode or forward sFlow datagrams. This
registration provides its source outputs; the Docker integration is separate.

| Input or action | Before | After |
| --- | --- | --- |
| Build the pinned sflowtool source | Make clones the revision and runs `boot.sh`, `configure`, Make and Debian packaging | A declared `rules_foreign_cc` action runs the same upstream Autoconf/Make build with SONiC's selected GCC and shared execution tools |
| Supply `/usr/bin/sflowtool` to `docker-sflow` | Import the Make-built DEB | Consume `@sflowtool//:runtime` directly |
| Inspect native symbols | The legacy `dh_strip` override retains the executable's debug data | `@sflowtool//:sflowtool` retains the unstripped binary; runtime and matching detached symbols derive from that same linked ELF |

No DEB is generated, no Make package cache is required, and the legacy SONiC
Make/Debian path is unchanged. The only linked target dependency is libc from
the selected toolchain sysroot. Upstream has no test suite at this revision;
`package_test` exercises the installed artifact instead of inventing upstream
test coverage.

Public targets:

- `@sflowtool//:runtime`: `/usr/bin/sflowtool` (root, 0755) and the unchanged
  upstream `COPYING` notice at `/usr/share/doc/sflowtool/copyright`.
- `@sflowtool//:runtime.debug_symbols`: symbols from the same deployed ELF.
- `@sflowtool//:sflowtool`: unstripped executable for inspection.
- `@sflowtool//:configuration` and `:configure_log`: generated configure evidence.
- `@sflowtool//:package_test`: installed paths, metadata, architecture, libc-only
  linkage, build ID/debug-link/GDB checks including a negative control;
  sFlow v5 interface-counter decoding with IPv4 and IPv6 agent addresses;
  byte-for-byte forwarding to a private UDP collector; unsupported-version
  rejection.

Native AMD64/Trixie is the declared matrix. The registry's normal PR CI builds
all named outputs and runs the installed test from a fresh external consumer.
No full VS image, physical sampling or kernel psample behavior is claimed.

The compilation cache boundary is the upstream configure/Make action. Editing
any declared source reruns that action; packaging and consumers are separate
Bazel actions. Normal builds do not regenerate maintained BUILD definitions.
To add upstream files, keep them in the declared source tree; to change installed
paths, update the small runtime target and its independent installed inventory.
