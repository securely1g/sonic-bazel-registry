# SONiC DASH API

`0.0.3-47315bf9cdfa90c04cac3fbf6dbaca8526841169` builds DASH API from
[`securely1g/sonic-dash-api` commit `47315bf`](https://github.com/securely1g/sonic-dash-api/commit/47315bf9cdfa90c04cac3fbf6dbaca8526841169).
The only registry patch sets the module version. Source definitions, packaging,
and regression tests remain in the DASH repository.

The source snapshot does not contain `MODULE.bazel.lock`. Bazel regenerates this
ignored file for local and CI builds; native source CI retains it as resolution
evidence. Module versions, registry pins and source integrity declarations stay
in their owning modules. The module version is independent of the unchanged
`libdashapi` Debian package version `1.0.0`.

The source CI image and APT sources form a compatible pinned environment:
Debian Trixie from July 13, Debian snapshot `20260727T143429Z`, and security
snapshot `20260726T121236Z`. The source workflow retains APT policy and installed
package evidence for its real-package tests.

Consumers declare the source module with a local repository name:

```starlark
bazel_dep(
    name = "sonic-dash-api",
    version = "0.0.3-47315bf9cdfa90c04cac3fbf6dbaca8526841169",
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
tests the installed package with Debian Python protobuf. Build-time protoc and
SWIG remain execution tools; linked libraries remain target dependencies.

## Runtime and matching debug packages

The module preserves the Debian library, headers, Python module, and CLI paths.
Its package targets are:

| Target | Output |
| --- | --- |
| `@sonic_dash_api//:libdashapi_deb` | Runtime `libdashapi` Debian package |
| `@sonic_dash_api//:libdashapi_dbg_deb` | Matching detached symbols Debian package |
| `@sonic_dash_api//:libdashapi_pkg` | Runtime deployment tar |
| `@sonic_dash_api//:libdashapi_pkg.debug_symbols` | Matching symbols tar |

Both the library and Python extension contribute symbols. Runtime copies and
detached symbols come from the same linked binaries; package tests verify
build IDs, debug links, and GDB source-line lookup.

## Native registry validation

The presubmit creates a separate Bazel consumer on native Debian
Trixie AMD64 and ARM64. It selects infrastructure
`0.0.10-7bc84c13cb812d0cf576485009352bbc96dde00a`, builds the four package
outputs and a dynamic C++ consumer, and runs these source-owned tests uncached:

- `//bazel:source_contract_test` checks the complete 96-file installed layout,
  ELF architecture, ABI dependencies, package metadata, and matching symbols.
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
stack base. Downstream SWSS migration and SONiC image assembly need their own
resolved-graph and runtime validation.
