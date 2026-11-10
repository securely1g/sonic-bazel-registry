# DASH recursive Make compiler and linker flags

The [DASH source](https://github.com/securely1g/DASH/commit/24a36627c27520d5ad230153944fd14599a1015f) builds
the SAI API through its existing Makefile. Its launch adapter carries long
compiler and linker argument vectors across recursive Make without exceeding
Linux's per-string argument limit. It preserves flag ordering and the generator
and linker options used by [Syncd VS](https://github.com/securely1g/sonic-buildimage/pull/133)
and [Gearbox](https://github.com/securely1g/sonic-buildimage/pull/154).

The registry applies one version patch to the source module. Consumers resolve
the PI `0.1.3.sonic.4` SDK and the shared build-infra `.28` implementation
through their registry. The candidate uses the same published P4C
`1.2.4.2.sonic.3` and Distroless `0.9.4.sonic.18` recipes as its source.

Native AMD64 and ARM64 checks build `//:sdk`, `//:runtime`,
`//:runtime.debug_symbols` and `//:runtime_packages.json`. The runtime test
checks the installed TARs and debug data. The recursive Make test exercises
ordered compilation/linking and the original oversized environment failure.
