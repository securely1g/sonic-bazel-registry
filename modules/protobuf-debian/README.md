# protobuf-debian

`3.21.12-sonic.1` provides matching Debian 13 (Trixie) protobuf generation and
the C++ shared-library interface for native Linux AMD64 and ARM64 consumers.
It retains SONiC's `libprotobuf.so.32` ABI. The upstream version is 3.21.12;
upstream names its source release `v21.12`. That archive records provenance;
the compiler, target headers, and runtime come from the shared SONiC Debian
snapshot and include Debian's fixes.

## Interfaces

```starlark
bazel_dep(name = "protobuf-debian", version = "3.21.12-sonic.1", repo_name = "protobuf_debian")
load("@protobuf_debian//:defs.bzl", "cpp_proto_sources", "python_proto_sources")
```

- `@protobuf_debian//:libprotobuf` provides target headers and only the full shared
  library, excluding the Debian development package's unrelated lite link inputs.
- `@protobuf_debian//:protoc` aliases the shared infrastructure executable.
- `cpp_proto_sources` generates `.pb.cc` and `.pb.h` labels and `sources`/`headers`
  output groups.
- `python_proto_sources` generates `_pb2.py` and `_pb2.pyi` labels and `python`/`pyi`
  output groups. Consumers declare their Python protobuf runtime separately.

Both macros accept `srcs`, `strip_import_prefix`, and `output_prefix`. For example,
`srcs = ["proto/item.proto"]`, `strip_import_prefix = "proto"`, and
`output_prefix = "generated"` expose `:generated/item.pb.h` or
`:generated/item_pb2.py`. Inputs must lie within the caller's repository/package
subtree. Include imported proto sources in `srcs`; all selected inputs generate
outputs. Well-known proto imports come from the matching compiler payload.

The compiler is selected with `cfg = "exec"`. Its loader, libraries, and include
files come from `sonic-build-infra`'s shared `build_tools` set. Target libraries
remain in the target configuration. Both sets use the same shared Debian source
snapshot; this module has no separate downloader or Debian package lock.

This module is separate from BCR's `protobuf` module and does not replace the
protobuf version used by unrelated Bazel rules. The patched Distroless importer
retains protobuf's required `.inc` header fragments.

## Validation

Registry CI natively runs AMD64 and ARM64 generation, binary and JSON round
trips, exact runtime selection and ELF SONAME/machine checks, and Python/stub
syntax checks. The shared infrastructure source CI exercises C++, Python, and
stub generation with a proto3 optional field and a well-known timestamp import.
