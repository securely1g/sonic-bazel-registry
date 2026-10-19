# Debian GCC toolchains

This registers landed build-infrastructure commit
`0c1d31528ad50c6505117a6df7409ccebee863cf` from
[build-infra #49](https://github.com/securely1g/sonic-build-infra/pull/49).
Native AMD64, native ARM64, and AMD64-to-ARM64 GCC use the pinned Debian
compiler packages and the shared sysroot also used by Clang. Existing
compiler and binutils target names remain available.

Registry CI imports the module into a fresh Bazel 8.5.1 consumer on native
AMD64 and ARM64. It builds C and C++ programs, a shared library, configure/Make
outputs, and matching runtime/debug TARs; tests exercise compiler launchers,
Kerberos generators, position-independent code, and stripped/debug contents.
The selected targets do not produce DEB packages.

The source's independent shared-sysroot consumer additionally exercises
GCC and Clang, source generators, static archives and cross-build execution
on native ARM64. Those checks belong to the
[source workflow](https://github.com/securely1g/sonic-build-infra/blob/0c1d31528ad50c6505117a6df7409ccebee863cf/.github/workflows/bazel.yml);
the registry matrix verifies native consumers and does not claim cross execution.

Consumers should request `0.0.16-0c1d31528ad50c6505117a6df7409ccebee863cf`.
Commit suffixes do not sort by source date: use a root `single_version_override`
when another dependency requests a lexically higher `0.0.16` snapshot. Check
the selected module graph and fetched MODULE declaration after updating pins.
