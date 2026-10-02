# protobuf-legacy

`3.21.12-sonic.1` builds Protobuf's compiler and C++ runtime from the upstream
`v21.12` source archive (the C++ version is 3.21.12). It supports native Linux
AMD64 and ARM64. No Protobuf compiler, header or library comes from a Debian
package.

The separate module name keeps this runtime at 3.21.12 while Bazel tooling can
resolve its newer BCR `protobuf` dependency independently. BCR does not publish
the exact 21.12 release. This integration preserves upstream `BUILD.bazel` and
`protobuf.bzl`; small patches adapt Bazel 8 rule imports, retain every public
runtime object when linking a shared library, and add Python typing-stub output
to upstream `proto_gen`.

## Consumer interfaces

```starlark
bazel_dep(name = "protobuf-legacy", version = "3.21.12-sonic.1", repo_name = "protobuf_legacy")
load("@protobuf_legacy//:defs.bzl", "cpp_proto_sources", "python_proto_sources")
```

- `:protoc` is upstream's source-built compiler. Generation selects it in the
  execution configuration. Compiler and runtime use the same pinned archive.
- `:libprotobuf` provides upstream headers and a shared-only C++ link interface.
  It retains SONAME `libprotobuf.so.32`, even for consumers with `linkstatic=True`.
  Consumers must use this target rather than upstream's static `:protobuf`.
- `:shared_library` exposes the linked `libprotobuf.so.32` file.
- `:libprotobuf_pkg` installs the stripped runtime under
  `/usr/lib/<multiarch>/libprotobuf.so.32.0.12`, its `libprotobuf.so.32` symlink,
  and the upstream license. `:libprotobuf_pkg.debug_symbols` carries the matching
  build-ID debug file. Install these tars together with consumers; their runtime
  must select this source-built library rather than a Debian Protobuf package.
- `cpp_proto_sources` provides `.pb.cc` and `.pb.h` labels and `sources`/`headers`
  output groups. `python_proto_sources` provides `_pb2.py` and `_pb2.pyi` labels
  and `python`/`pyi` output groups. Both use upstream `proto_gen`; a small adapter
  preserves the installed output paths required by DASH. Consumers declare their
  Python Protobuf runtime separately.

The generation macros accept `srcs`, `strip_import_prefix`, and `output_prefix`.
For example, `proto/item.proto` with `strip_import_prefix = "proto"` and
`output_prefix = "generated"` produces `:generated/item.pb.h` or
`:generated/item_pb2.py`. Inputs belong to the caller's package; list imported
local schemas in `srcs`. Well-known types come from this same upstream release.

## Validation

Native AMD64 and ARM64 presubmits select the compiler, shared library, generated
C++/Python/stub files, and runtime/debug tars. Tests assert compiler/header version
3.21.12, proto3 optional and well-known-type generation, binary/JSON round trips,
SONAME and exact runtime selection, installed tar layout and root ownership,
matching build IDs/debug-link CRCs, and GDB source-line lookup. No DEBs are built.
