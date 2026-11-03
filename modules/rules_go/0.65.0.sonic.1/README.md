# Content-derived Go build IDs for SONiC

The OTEL source producer in [sonic-buildimage issue #100](https://github.com/securely1g/sonic-buildimage/issues/100)
preserves the official collector's pure-Go, CGO-disabled Go 1.25.6 contract.
Its runtime and detached symbols need IDs that identify the linked bytes.
The older rules_go uses the fixed Go ID `redacted`; Go derives a fixed GNU ID
from that placeholder, so different binaries can have the same IDs.

This entry reuses upstream rules_go 0.65.0, including
[#4728](https://github.com/bazel-contrib/rules_go/pull/4728) and
[#4764](https://github.com/bazel-contrib/rules_go/pull/4764)'s content-derived
Go/GNU IDs and streaming implementation. It adds no SONiC build-ID writer,
keeps the collector's CGO mode, and generates no DEBs.

The published 0.64.1-sonic.1 entry is unchanged. Its #4583 relative external
CGO-header patch is absent from upstream 0.65.0 and is carried forward
byte-for-byte, with both original native regression cases and all fixtures.
Only its filename is normalized. The old version-only MODULE patch is replaced
by the existing registry MODULE overlay generator for the new version.

CI retains the existing native AMD64/ARM64 header-regression matrix. It also
selects upstream's original native ELF build-ID tests, covering different pure
Go/CGO binaries, explicit user IDs, and a native-code-only edit. The separate
Darwin/ARM64 cross-build test is outside this Linux migration scope; its source
is retained unchanged and is not selected. Collector conversion remains AMD64
only. Go 1.25.6 is selected for the external registry consumer.

Local acceptance uses the real upstream OpenTelemetry Collector Builder
`v0.144.0`, with its locked `x/mod v0.32.0` and `x/sys v0.36.0` dependencies:

| Input or action | 0.64.1-sonic.1 | 0.65.0.sonic.1 |
| --- | --- | --- |
| Edit the builder's actual command help | Executable/help bytes change; Go/GNU IDs remain fixed | Executable bytes and both IDs change |
| Build in two different-length output roots with uncached GoLink actions | Not used for the positive proof | Complete executable bytes and both IDs match |
| Restore the source and use the ordinary registry consumer | Original bytes and fixed IDs return | Original bytes and content-derived IDs return |
| Generate the pinned collector release manifest | All five files match the original generator | The same five files match, with host programs unavailable |

Both original CGO header tests reproduce the missing-header failure with
unpatched public 0.65.0 and pass with this entry. The upstream native content-ID
and native-only-edit tests also pass with Go 1.25.6. Action graphs are checked
for DEB outputs and package-generation wrappers before execution.

The real builder proof establishes source generation and build-ID behavior.
Full collector compilation, runtime/debug TAR acceptance, component parity and
Docker integration remain the separate OTEL producer/consumer work.
