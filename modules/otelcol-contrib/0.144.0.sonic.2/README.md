# OpenTelemetry Collector Contrib source build

This entry supplies the AMD64 source producer for SONiC's `docker-sonic-otel`
([package issue #100](https://github.com/securely1g/sonic-buildimage/issues/100),
[image issue #127](https://github.com/securely1g/sonic-buildimage/issues/127)).
It uses the upstream 0.144.0 release manifest at
`9e444f54f4033bf6b7c254f0a8797ffd3917b6de`, including every manifest component.

Upstream OCB generates the entrypoints. The declared generation action disables
module fetching and compilation; standard `rules_go` actions compile the result.
The collector uses Go 1.25.6, pure Go, AMD64 v1, normal optimization, and the
Go 1.24 compatibility defaults observed in the official release binary.
The existing shared `keep_debug_info` rule retains DWARF even under consumer
strip settings; the Go SDK wrapper keeps optimized compilation. Runtime and debug
TARs split the same binary. No DEBs are generated.

`go.mod` and `go.sum` are canonical reviewed locks. The 1,007 dependency versions
and checksums reported by the official release binary match those locks. OCB's
tool dependencies use a separate standard Gazelle extension instance, keeping
them out of the runtime module graph. Standard Gazelle generation uses the
locked modules' checked-in `.pb.go` files, matching the original `go build`;
it does not add a protoc regeneration step. There is no custom module resolver.

Consumers add the following standard Gazelle policy to their root `MODULE.bazel`
after declaring this module. Gazelle requires this policy in the root; the owner
continues to supply the complete sources, dependency locks and targets. The
registry's ordinary `integration` consumer exercises the same public declarations
without source overrides or experimental flags:

```starlark
otel_runtime_deps = use_extension("@otelcol-contrib//bazel:collector_deps.bzl", "go_deps")
otel_runtime_deps.gazelle_default_attributes(
    build_file_generation = "clean",
    directives = ["gazelle:proto disable_global"],
)
# Preserve the receiver's embedded YAML across the nested Go-test package.
otel_runtime_deps.module_override(
    path = "github.com/open-telemetry/opentelemetry-collector-contrib/receiver/googlecloudspannerreceiver",
    patch_strip = 1,
    patches = ["@otelcol-contrib//bazel:0001-googlecloudspannerreceiver-embedded-metadata.patch"],
)
```

The component groups in `components.bzl` are maintained directly. When changing
the release manifest, update those groups and locks together. The source contract
test compares them with upstream OCB's generated imports and manifest versions;
normal builds never regenerate BUILD definitions.

Public interfaces are `:otelcol-contrib`, `:runtime`, `:runtime.debug_symbols`,
`:runtime_packages.json`, and `:sources`. The source TAR contains the generated
collector entrypoints, manifest and locks, not copies of every upstream dependency.
Runtime metadata reads the exact finalized control from the existing official
AMD64 package; its URL and checksums are recorded in the overlay. This is a
metadata input, not a Debian package definition or producer. Image-owned account,
symlink, supervisor and SONiC configuration effects remain in issue #127.

Validation is in progress. The native AMD64 collector and runtime/debug/source
TARs built through the ordinary integration consumer. Installed checks passed the
original startup/golden tests, all 1,007 release dependency versions/checksums,
configuration validation and matching debug symbols. The final metadata action
needs [build-infra #77](https://github.com/securely1g/sonic-build-infra/pull/77).
The complete declared package test, clean/incremental acceptance, reproducibility
and image integration remain pending.

The public `:package_test` additionally consumes the original upstream golden
command. Consumers running that installed test configure its separate standard
Gazelle extension at the root, without modifying the collector's runtime locks:

```starlark
otel_golden_deps = use_extension("@otelcol-contrib//bazel:golden_deps.bzl", "go_deps")
otel_golden_deps.gazelle_default_attributes(
    build_file_generation = "clean",
    directives = ["gazelle:proto disable_global"],
)
```

The native AMD64 integration test retains the release's ten-second startup check,
original expected golden metrics and all original ignore options. Only test
endpoints move to loopback; port8888 is retained and the test is exclusive. It
also checks exact installed/runtime-source TAR contents, the verified official
version/components output, invalid configuration rejection, static ELF and
matching GNU debuglink/build-ID/GDB behavior. A test-only reader uses Go’s standard
`debug/buildinfo` package to verify the final binary’s 1,007 linked modules and
checksums, SDK and build settings; stripping must preserve that metadata. Native
registry CI supplies GDB.
The tool's Go lock is independent of the 1,007 production dependency versions.
The upstream `components` command ranges an unsorted map for configuration
providers. Its comparison sorts only those complete provider records; every
other byte, field and sequence remains exact. Malformed and duplicate provider
records fail, with focused negative controls in the source-contract suite.
