## Registry dependency refresh: `0.0.4-42d274f1ba5aa8f248ef4bb9f2fce9e0a0738164`

Source: `securely1g/DASH@42d274f1ba5aa8f248ef4bb9f2fce9e0a0738164`, based on `a9b799bb664b3b3b9d6e9a19cedd38b620e769de`. Dependency targets are frozen to published registry snapshot `3d1cc5e8dfd553d2acbe4198e504a245e6bdbddf`. The source owns the module base version and dependency updates. The registry supplies the full commit-qualified identity and retains its existing integration behavior.

Full archive patch-application and build validation must be recorded separately.

# DASH recursive Make compiler and linker flags

The [DASH source](https://github.com/securely1g/DASH/commit/2cbfdfa1205c0d03003444e5c80f89adb8c3df59) builds
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
