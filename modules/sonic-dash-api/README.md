# SONiC DASH API

`0.0.4-c28c2c28b2db56163d5b9c48497c0eee2379f7fd` builds DASH from
[source commit `c28c2c2`](https://github.com/securely1g/sonic-dash-api/commit/c28c2c28b2db56163d5b9c48497c0eee2379f7fd).
The registry patch only sets its module version. Build definitions and tests
remain in [DASH PR #1](https://github.com/securely1g/sonic-dash-api/pull/1).

```starlark
bazel_dep(
    name = "sonic-dash-api",
    version = "0.0.4-c28c2c28b2db56163d5b9c48497c0eee2379f7fd",
    repo_name = "sonic_dash_api",
)
```

The public `@sonic_dash_api//:dashapi` target provides generated C++ headers
and `libdashapi.so`; `@sonic_dash_api//misc:dash_api` provides Python bindings.
All 30 schemas are generated with source-built Protobuf 3.21.12 from
[registry #25](https://github.com/securely1g/sonic-bazel-registry/pull/25).
Both DASH shared libraries use the same source-built `libprotobuf.so.32`.
The Python runtime remains a separate pinned dependency.

## Deployment archives

| Target | Output |
| --- | --- |
| `@sonic_dash_api//:libdashapi_pkg` | DASH runtime tar: library, headers, Python bindings and CLI |
| `@sonic_dash_api//:libdashapi_pkg.debug_symbols` | Matching DASH debug tar |
| `@sonic_dash_api//:protobuf_runtime_pkg` | Source-built Protobuf runtime tar |
| `@sonic_dash_api//:protobuf_debug_pkg` | Matching Protobuf debug tar |

The existing 96-file DASH payload is preserved. Protobuf archives remain
separate so consumers can share the runtime layer. Each debug tar is produced
from the same linked binaries as its runtime tar; no DEB is produced.
[Registry #23](https://github.com/securely1g/sonic-bazel-registry/pull/23)
provides the shared rules that preserve root ownership for non-root builders.

## Validation

Native AMD64 and ARM64 presubmits build the four archives and run the source
contract, C++ runtime, utility and Python tests. Checks cover the installed
layout, serialization, imported Protobuf symbols, the actual loaded library,
ELF architecture, build IDs, debug links and GDB source lookup.

CI retains outputs and generated Bazel resolution evidence. Consumers use one
reviewed SONiC registry branch containing this entry and its prerequisites,
plus Bazel Central Registry; non-CI snapshot selection follows repository policy.
SWSS integration and full image assembly require their own validation.
