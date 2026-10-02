# SONiC DASH API

`0.0.4-d465b786157fd9021b1600062155752e0601e31d` builds DASH API from
[`securely1g/sonic-dash-api` commit `d465b78`](https://github.com/securely1g/sonic-dash-api/commit/d465b786157fd9021b1600062155752e0601e31d).
The registry patch sets the module version and selects the merged shared-protoc
dependency published by [registry #24](https://github.com/securely1g/sonic-bazel-registry/pull/24).
The source archive remains unchanged. Source definitions, deployment archives,
and regression tests remain in the DASH repository. The source PR still selects
the prior infrastructure snapshot; this registry entry adapts its dependency
metadata so the current registry stack resolves the landed implementation.

The source snapshot does not contain `MODULE.bazel.lock`. Bazel regenerates this
ignored file for local and CI builds; native source CI retains it as resolution
evidence. Module versions, registry pins and source integrity declarations stay
in their owning modules. The Bazel outputs are runtime and matching detached-symbol tar archives.

The source CI image and APT sources form a compatible pinned environment:
Debian Trixie from July 13, Debian snapshot `20260727T143429Z`, and security
snapshot `20260726T121236Z`. The source workflow retains APT policy and installed
package evidence for its installed-tar tests.

Consumers declare the source module with a local repository name:

```starlark
bazel_dep(
    name = "sonic-dash-api",
    version = "0.0.4-d465b786157fd9021b1600062155752e0601e31d",
    repo_name = "sonic_dash_api",
)
```

The public C++ target `@sonic_dash_api//:dashapi` exports the generated
`dash_api` headers and source-built `libdashapi.so`. The public Python target is
`@sonic_dash_api//misc:dash_api`. The module generates C++ and Python bindings
for all 30 protobuf schemas, builds the utility implementation and SWIG
extension, and includes the existing Python CLI. It uses the reusable
`protobuf-debian` module for matching execution-side `protoc` and target-side
protobuf runtime dependencies. It does not fetch prebuilt DASH packages.

External pinned packages are intentional inputs: Debian protobuf provides target
headers and libraries, Debian Boost supplies utility-test dependencies, and a
hash-pinned protobuf wheel supplies the Bazel Python runtime. Source CI also
tests the extracted runtime tar with Debian Python protobuf. Build-time protoc and
SWIG remain execution tools; linked libraries remain target dependencies.

## Runtime and matching debug archives

The module preserves the Debian library, headers, Python module, and CLI paths.
Its archive targets are:

| Target | Output |
| --- | --- |
| `@sonic_dash_api//:libdashapi_pkg` | Runtime deployment tar |
| `@sonic_dash_api//:libdashapi_pkg.debug_symbols` | Matching symbols tar |

Both the library and Python extension contribute symbols. Runtime copies and
detached symbols come from the same linked binaries; archive tests verify
build IDs, debug links, and GDB source-line lookup.

## Native header importer

This source version selects `rules_distroless 0.9.4-sonic.1` from
[registry PR #28](https://github.com/securely1g/sonic-bazel-registry/pull/28).
Its protobuf `.inc` header fix supports the native AMD64/ARM64 matrix. Consumers
with historical dotted Distroless requirements must also use a root
`single_version_override` for this version; those older names sort above it.
The presubmit selects and checks the fetched Distroless declaration explicitly.

## Native registry validation

The presubmit creates a separate Bazel consumer on native Debian
Trixie AMD64 and ARM64. It selects infrastructure
`0.0.14-5859f7e63b6bff0f601a9b8d00853fa3ae7f216e`, builds both tar
outputs and a dynamic C++ consumer, and runs these source-owned tests uncached:

- `//bazel:source_contract_test` checks the complete 96-file installed layout,
  ELF architecture, ABI dependencies, ownership, modes, and matching symbols.
- `//bazel:runtime_consumer_test` exercises the C and C++ interfaces through the
  built shared library, including a protobuf round trip.
- `//bazel:utils_test` runs the existing five C++ utility tests.
- `//misc:python_test` imports all generated Python modules and stubs, checks
  optional-field and timestamp behavior, and runs the existing CLI pytest.

The runner retains fetched module declarations, build outputs, resolved
module information, and test evidence. These external consumer checks are
additional to the native source CI in
[sonic-dash-api PR #1](https://github.com/securely1g/sonic-dash-api/pull/1).
The matching shared protobuf and infrastructure entries are provided by the
[registry PR #25](https://github.com/securely1g/sonic-bazel-registry/pull/25)
stack base. Consumers select one immutable snapshot containing the required
registrations, plus Bazel Central Registry. Downstream SWSS migration and SONiC image assembly need their own
resolved-graph and runtime validation.
