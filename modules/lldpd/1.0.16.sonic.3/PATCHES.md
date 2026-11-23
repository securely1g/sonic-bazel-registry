# Patch provenance

The prepared source applies Debian's `debian/patches/series` from the fixed
`lldpd_1.0.16-1+deb12u1.debian.tar.xz` archive first, then the maintained SONiC
series, then the Bazel integration patch below.

| Patch | Source and purpose | Upstream status |
| --- | --- | --- |
| `0001-return-error-when-port-does-not-exist.patch` | SONiC `src/lldpd/patch`; preserve failure when a requested interface does not exist. | Retained SONiC patch. |
| `0002-use-a-different-socket-for-changes-and-queries.patch` | SONiC `src/lldpd/patch`; separate netlink notification and query sockets. Retains the existing registry patch bytes, including its hunk-count correction. | Retained SONiC patch. |
| `0003-use-explicit-libbsd-headers.patch` | Registry adaptation; use libbsd's public `bsd/stdlib.h` and `bsd/unistd.h` instead of relying on system include directory ordering. Preserves the configured `strtonum` and `setproctitle` implementations. | Local integration patch. |

The third patch changes product header includes only. It changes neither
`configure`, `configure.ac`, the M4 tests, nor their input templates. Target
configuration probes use the original Debian and SONiC patch chain; native
compilation uses the complete chain above. The generated public API consumer
and unchanged upstream suites exercise the resulting linked implementation.
