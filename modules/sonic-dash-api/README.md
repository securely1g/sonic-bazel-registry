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

The source CI image and APT sources now form a compatible pinned environment:
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

The new version's presubmit creates a separate Bazel consumer on native Debian
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

## Previous source versions

`0.0.2-85eae7edb05ee93faec768979ec502805a5717d7` is retained unchanged with its generated,
untracked lockfile policy. The current source version adds pinned CI APT
installation and documents the supported external binary dependencies.


`0.0.1-64985db0113ab06d9ae058fed53676e4c129d8c8` is retained unchanged, including its
source archive and presubmit. It builds the same native interfaces and package
outputs with the earlier checked-in dependency lock. The current source version
above implements the generated, untracked lockfile policy.

## Historical prebuilt version

`0.0.0-7af4056f7393b2ccbca9fc2d9aa668251e55b0a7` remains unchanged for existing
consumers. It imports the recorded AMD64 or ARM64 `libdashapi_1.0.0` package
from public Azure build artifacts, with package and archive provenance in its
source-owned `bazel/prebuilt.json`. Its original module, source archive,
version patch, and presubmit are retained byte-for-byte.

That version uses infrastructure
`0.0.7-91fe8246519f99838da936eee54e85208c704a4d`, whose historical registry
entry is preserved in the stack. Its `//:prebuilt_files` output and two
prebuilt contract/runtime tests describe the former import boundary; the new
version above replaces that boundary with source generation and compilation.
