# OpenTelemetry Collector Contrib 0.165.0

The SONiC VS installer includes `docker-sonic-otel`, whose Dockerfile installs
the official Linux AMD64 Collector 0.165.0 Debian package. This entry builds the
collector executable and installation TAR from the upstream release manifest.
The detached symbols and runtime TAR come from the same executable. The official
Debian package supplies the test reference and its finalized control metadata.
[Release sources](https://github.com/open-telemetry/opentelemetry-collector-releases/tree/b9425f263115f328bc3bd4e65b825101b499f144)

The upstream OpenTelemetry Collector Builder (OCB) generates the collector's Go
entrypoints. The registered `go.mod` and `go.sum` come from running OCB 0.165.0
on the release manifest with the Go 1.27.3 SDK. OCB and the upstream golden
test program have separate tooling locks. Each of the three Go graphs also
exports a Gazelle ZIP lock. Consumers bind those locks in their root workspace
so Bazel downloads content-verified dependency archives even if the default
SDK predates a dependency's minimum Go version. Bazel generates entrypoints without
network access and compiles all 255 configured components with `rules_go`.

The manifest adds the OBI eBPF receiver. Upstream releases its generated BPF
objects in a separate source archive. The integration workspace fetches that
archive by SHA-256 and uses the release's Avro replacement from the collector's
Go lock. The registered `rules_go 0.65.0.sonic.3` linker preserves the two
replacement records on the linked executable. The installed-package test checks
all 1,087 reachable Go dependencies against the published binary, including the
original and replacement module identities. It also runs the collector startup
and upstream golden metrics checks.

Image consumers can use the registered `:otelcol-contrib`, `:runtime`,
`:runtime.debug_symbols`, `:runtime_packages.json` and `:sources` targets.
Select the registered Go rules and apply the root Gazelle declarations from
[integration/MODULE.bazel](integration/MODULE.bazel).

The integration fixture uses Go 1.26.7 as its root SDK. The collector, builder,
build-info reader and golden executable select the official release SDK 1.27.3.

## Refreshing the locks and references

Use the pinned release's `scripts/prepare-obi.sh otelcol-contrib` and OCB with
`--config manifest.yaml --skip-compilation` from
`distributions/otelcol-contrib`. Copy the resulting `_build/go.mod` and
`_build/go.sum` and update the maintained component groups from the generated
imports. Refresh OCB and golden tool locks at the matching version. For each
private Gazelle extension use its `bazel_gazelle_go_repository_config//:zip-lock.json`
plan with the sonic-build-infra Go lock updater. Generate each SHA-256 from the
module ZIP verified against the corresponding plan's Go `h1` content checksum. The source
contract test compares those imports with the maintained Bazel dependency list.

The reference Debian archive and executable digests, command outputs and Go
build information are recorded in
[release-provenance.json](overlay/bazel/testdata/release-provenance.json).
